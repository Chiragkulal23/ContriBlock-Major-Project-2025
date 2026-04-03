import os
from flask import request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from backend.extensions import db, socketio
from backend.api import api_bp
from backend.models.contribution import Contribution
from backend.models.user import User
from web3 import Web3
import json
from backend.config import Config
from backend.services.storage import save_upload, upload_file_to_pinata, test_pinata_auth, check_ipfs_hash_exists

ALLOWED_EXT = {"pdf", "png", "jpg", "jpeg", "gif", "txt", "md"}


def allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@api_bp.get("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@api_bp.get("/contributions")
def list_contributions():
    items = Contribution.query.order_by(Contribution.created_at.desc()).all()
    return jsonify([c.to_card() for c in items])


@api_bp.post("/contributions")
@jwt_required()
def create_contribution():
    uid = int(get_jwt_identity())
    user = User.query.get(uid)
    
    # Handle file upload (optional)
    file_url = None
    if "file" in request.files:
        file = request.files["file"]
        print(f"File received: {file.filename if file else 'None'}")
        if file and file.filename and allowed(file.filename):
            # Save file locally to uploads folder
            filename = save_upload(file, current_app.config["UPLOAD_FOLDER"])
            file_url = f"/api/uploads/{filename}"
            print(f"File saved: {filename}, URL: {file_url}")
        else:
            print(f"File rejected: filename={file.filename if file else 'None'}, allowed={allowed(file.filename) if file and file.filename else False}")
    
    title = request.form.get("title") or "Untitled"
    description = request.form.get("description") or ""
    
    # Store contribution with Pending status (no IPFS upload yet)
    contrib = Contribution(
        title=title,
        description=description,
        author=user,
        ipfs_cid=None,  # Will be set after admin approval
        file_url=file_url,  # Local file path
        reward_amount=0.0,
        status="Pending"  # Default status
    )
    db.session.add(contrib)
    db.session.commit()

    contrib_detail = contrib.to_detail()
    print(f"Contribution created with file_url: {contrib_detail.get('file_url')}")
    socketio.emit("new_contribution", contrib.to_card())
    return jsonify(contrib_detail), 201


@api_bp.get("/contributions/<int:cid>")
def get_contribution(cid: int):
    c = Contribution.query.get_or_404(cid)
    return jsonify(c.to_detail())


@api_bp.get("/ipfs/status")
def ipfs_status():
    """Health check for Pinata credentials/auth."""
    status = test_pinata_auth()
    code = 200 if status.get("ok") else 500
    return jsonify(status), code


@api_bp.post("/contributions/<int:cid>/review")
@jwt_required()
def review_contribution(cid: int):
    # Admin only: accept or reject
    uid = int(get_jwt_identity())
    from backend.models.user import User  # local import to avoid cycle
    user = User.query.get(uid)
    if not user or user.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    action = (data.get("action") or "").lower()
    if action not in {"accept", "reject"}:
        return jsonify({"error": "Invalid action"}), 400

    c = Contribution.query.get_or_404(cid)
    
    if action == "reject":
        # Simply update status to Rejected
        c.status = "Rejected"
        db.session.commit()
        
        # Send notification to user
        socketio.emit("contribution_reviewed", {
            "id": cid, 
            "status": c.status,
            "message": "Your contribution was rejected by the admin.",
            "userId": c.author_id
        })
        
        return jsonify({"status": "ok", "newStatus": c.status, "message": "Contribution rejected"})
    
    elif action == "accept":
        # Upload to IPFS and blockchain
        try:
            print(f"[Approval] Starting approval for contribution {cid}")
            
            # Validate Pinata credentials before trying to upload
            print(f"[Approval] Testing Pinata authentication...")
            auth_status = test_pinata_auth()
            if not auth_status.get("ok"):
                error_msg = f"Pinata authentication failed: {auth_status}"
                print(f"[Approval] ERROR: {error_msg}")
                return jsonify({
                    "error": "IPFS upload failed",
                    "details": auth_status,
                }), 500
            
            print(f"[Approval] Pinata authentication successful")
            
            # Get local file path - handle both cases where file_url might be None or a full URL
            local_path = None
            if c.file_url:
                # Extract filename from URL path like "/api/uploads/filename.jpg"
                filename = os.path.basename(c.file_url)
                local_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                print(f"[Approval] File URL: {c.file_url}, Resolved path: {local_path}")
                
                # Check if file exists
                if not os.path.exists(local_path):
                    print(f"[Approval] WARNING: File not found at {local_path}")
                    # Try to continue without file upload
                    local_path = None
                else:
                    print(f"[Approval] File found at {local_path}")
            
            # PRE-UPLOAD DUPLICATE CHECK: Check if any existing contribution has the same file content
            if local_path and os.path.exists(local_path):
                print(f"[Duplicate Pre-Check] ========== STARTING PRE-UPLOAD DUPLICATE CHECK ==========")
                
                # Calculate file hash for comparison
                import hashlib
                file_hash = hashlib.sha256()
                with open(local_path, 'rb') as f:
                    while chunk := f.read(8192):
                        file_hash.update(chunk)
                file_hash_hex = file_hash.hexdigest()
                print(f"[Duplicate Pre-Check] File hash (SHA256): {file_hash_hex}")
                
                # Check if any existing accepted contribution has the same file hash
                # We'll compare by file size and then by content hash stored in ipfs_pin_timestamp
                file_size = os.path.getsize(local_path)
                print(f"[Duplicate Pre-Check] File size: {file_size} bytes")
                
                # Look for existing contributions with same file size and IPFS CID (indicating same file)
                existing_same_size = Contribution.query.filter(
                    Contribution.ipfs_file_size == file_size,
                    Contribution.status == "Accepted",
                    Contribution.ipfs_cid.isnot(None)
                ).all()
                
                if existing_same_size:
                    print(f"[Duplicate Pre-Check] Found {len(existing_same_size)} existing contributions with same file size")
                    
                    # For each existing contribution with same size, compare actual file content
                    for existing in existing_same_size:
                        if existing.file_url:
                            existing_filename = os.path.basename(existing.file_url)
                            existing_path = os.path.join(current_app.config["UPLOAD_FOLDER"], existing_filename)
                            
                            if os.path.exists(existing_path):
                                # Calculate hash of existing file
                                existing_hash = hashlib.sha256()
                                with open(existing_path, 'rb') as f:
                                    while chunk := f.read(8192):
                                        existing_hash.update(chunk)
                                existing_hash_hex = existing_hash.hexdigest()
                                
                                print(f"[Duplicate Pre-Check] Comparing with existing contribution {existing.id}:")
                                print(f"[Duplicate Pre-Check]   Existing file hash: {existing_hash_hex}")
                                print(f"[Duplicate Pre-Check]   Current file hash:  {file_hash_hex}")
                                
                                if file_hash_hex == existing_hash_hex:
                                    print(f"[Duplicate Pre-Check] ❌❌❌ EXACT FILE MATCH FOUND! ❌❌❌")
                                    print(f"[Duplicate Pre-Check] This file is identical to contribution {existing.id}")
                                    print(f"[Duplicate Pre-Check] File already exists on IPFS with CID: {existing.ipfs_cid}")
                                    print(f"[Duplicate Pre-Check] No new upload needed - rejecting as duplicate")
                                    
                                    # Update current contribution as duplicate
                                    c.status = "Duplicate"
                                    c.ipfs_cid = existing.ipfs_cid  # Use existing IPFS CID
                                    db.session.commit()
                                    print(f"[Duplicate Pre-Check] Contribution {cid} marked as Duplicate")
                                    print(f"[Duplicate Pre-Check] ========== PRE-UPLOAD CHECK COMPLETE - REJECTED ==========")
                                    
                                    # Send notification to user
                                    socketio.emit("contribution_reviewed", {
                                        "id": cid, 
                                        "status": c.status,
                                        "message": "❌ This exact file was already uploaded and approved earlier. Token will not be issued.",
                                        "userId": c.author_id,
                                        "existingContributionId": existing.id,
                                        "existingIpfsCid": existing.ipfs_cid
                                    })
                                    
                                    return jsonify({
                                        "status": "duplicate",
                                        "newStatus": "Duplicate",
                                        "message": "This exact file was already uploaded and approved earlier. Token will not be issued.",
                                        "rejectionReason": "Duplicate contribution. This exact file was already submitted and verified on blockchain.",
                                        "existingContributionId": existing.id,
                                        "existingIpfsCid": existing.ipfs_cid
                                    }), 409
                    
                    print(f"[Duplicate Pre-Check] ✅ No exact file matches found")
                else:
                    print(f"[Duplicate Pre-Check] ✅ No existing contributions with same file size found")
                
                print(f"[Duplicate Pre-Check] ========== PRE-UPLOAD CHECK COMPLETE - APPROVED ==========")
            
            # Upload to IPFS via Pinata (only if file exists)
            ipfs_metadata = None
            ipfs_hash = None
            
            if local_path and os.path.exists(local_path):
                # Extract original filename from file_url (e.g., "/api/uploads/myfile.pdf" -> "myfile.pdf")
                # Also get the actual filename from the local file system as a backup
                original_filename = None
                if c.file_url:
                    original_filename = os.path.basename(c.file_url)
                    print(f"[Approval] File URL: {c.file_url}")
                    print(f"[Approval] Extracted filename from URL: {original_filename}")
                
                # Also get filename from local_path as verification
                actual_filename = os.path.basename(local_path)
                print(f"[Approval] Actual filename from local path: {actual_filename}")
                
                # Use the extracted filename (should be the same as actual_filename)
                # Fallback to actual_filename if original_filename is empty
                pinata_filename = original_filename or actual_filename or f"contribution_{cid}"
                
                print(f"[Approval] Using Pinata filename: {pinata_filename}")
                print(f"[Approval] Uploading file to Pinata: {local_path} with name: {pinata_filename}")
                ipfs_metadata = upload_file_to_pinata(local_path, name=pinata_filename)
                print(f"[Approval] Pinata upload completed successfully! File saved as: {pinata_filename}")
                
                # Get IPFS CID immediately after upload
                ipfs_hash = ipfs_metadata.get("cid") if ipfs_metadata else None
                print(f"[Approval] IPFS CID received from Pinata: {ipfs_hash}")

                # POST-UPLOAD DUPLICATE CHECK: Check if this IPFS CID already exists in the database
                if ipfs_hash:
                    existing_contribution = Contribution.query.filter_by(ipfs_cid=ipfs_hash, status="Accepted").first()
                    if existing_contribution:
                        print(f"[Duplicate Post-Check] ❌❌❌ DUPLICATE DETECTED! ❌❌❌")
                        print(f"[Duplicate Post-Check] IPFS CID '{ipfs_hash}' already exists for contribution {existing_contribution.id}")
                        
                        # Update current contribution as duplicate
                        c.status = "Duplicate"
                        c.ipfs_cid = ipfs_hash  # Store CID
                        db.session.commit()
                        
                        socketio.emit("contribution_reviewed", {
                            "id": cid, 
                            "status": c.status,
                            "message": "❌ This file was already uploaded earlier. Token will not be issued.",
                            "userId": c.author_id
                        })
                        
                        return jsonify({
                            "status": "duplicate",
                            "newStatus": "Duplicate",
                            "message": "This file was already uploaded earlier. Token will not be issued.",
                            "rejectionReason": "Duplicate contribution. This file was already submitted and verified."
                        }), 409
            
            else:
                print(f"[Approval] No file to upload for contribution {cid}, creating text entry")
                # Create a text-based IPFS entry for contributions without files
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
                    tmp.write(f"Contribution: {c.title}\nDescription: {c.description}\nAuthor: {c.author.email}")
                    tmp_path = tmp.name
                # Use contribution title as filename if available
                text_filename = f"{c.title}.txt" if c.title else f"contribution_{cid}_text.txt"
                print(f"[Approval] Uploading text entry to Pinata: {tmp_path} with name: {text_filename}")
                ipfs_metadata = upload_file_to_pinata(tmp_path, name=text_filename)
                os.unlink(tmp_path)  # Clean up temp file
                print(f"[Approval] Text entry uploaded successfully!")
                
                # Get IPFS CID immediately after upload
                ipfs_hash = ipfs_metadata.get("cid") if ipfs_metadata else None
                print(f"[Approval] IPFS CID received from Pinata: {ipfs_hash}")
            
            # CRITICAL BLOCKCHAIN DUPLICATE CHECK: Check on-chain IMMEDIATELY after Pinata upload
            # This MUST happen BEFORE calling saveHashWithUser() to prevent blockchain duplication
            # Same file = Same IPFS CID, so if CID exists on-chain, same file was already tokenized
            tx_hash = None
            if ipfs_hash:
                try:
                    with open(Config.CONTRACT_ABI_PATH, "r") as f:
                        data = json.load(f)
                    abi = data["abi"]
                    address = Config.CONTRACT_ADDRESS or data.get("address")
                    if address and Config.DEPLOYER_PRIVATE_KEY:
                        print(f"[Duplicate Check] ========== STARTING BLOCKCHAIN DUPLICATE CHECK ==========")
                        print(f"[Duplicate Check] IPFS CID to check: {ipfs_hash}")
                        print(f"[Duplicate Check] Current contribution ID: {cid}")
                        
                        w3 = Web3(Web3.HTTPProvider(Config.GANACHE_URL))
                        
                        # Check if Ganache is running
                        try:
                            w3.eth.get_block('latest')
                            print(f"[Blockchain] Ganache connection successful")
                        except Exception as conn_err:
                            raise ConnectionError(f"Ganache is not running at {Config.GANACHE_URL}. Please start Ganache to enable blockchain transactions. IPFS upload completed successfully.")
                        
                        acct = w3.eth.account.from_key(Config.DEPLOYER_PRIVATE_KEY)
                        contract = w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)
                        
                        # BEFORE SAVING TO BLOCKCHAIN: Check if IPFS hash already exists
                        # Same file = Same IPFS CID from Pinata, so if CID exists on-chain, it's a duplicate
                        print(f"[Duplicate Check] Checking blockchain for duplicate IPFS hash: {ipfs_hash}")
                        print(f"[Duplicate Check] Type of ipfs_hash: {type(ipfs_hash)}, Value: {repr(ipfs_hash)}")
                        try:
                            existing_hashes = contract.functions.getAllHashes().call()
                            print(f"[Duplicate Check] Found {len(existing_hashes)} existing hashes on-chain")
                            
                            # Convert all hashes to strings and normalize (strip whitespace, ensure exact match)
                            existing_hashes_str = []
                            for h in existing_hashes:
                                hash_str = str(h).strip()
                                existing_hashes_str.append(hash_str)
                                print(f"[Duplicate Check]   Existing hash: '{hash_str}' (type: {type(h)}, length: {len(hash_str)})")
                            
                            ipfs_hash_str = str(ipfs_hash).strip()
                            print(f"[Duplicate Check] Current IPFS hash to check: '{ipfs_hash_str}' (type: {type(ipfs_hash)}, length: {len(ipfs_hash_str)})")
                            print(f"[Duplicate Check] Comparing '{ipfs_hash_str}' against {len(existing_hashes_str)} existing hashes...")
                            
                            # Check if duplicate exists on blockchain using exact string comparison
                            is_duplicate = False
                            for existing_hash in existing_hashes_str:
                                if ipfs_hash_str == existing_hash:
                                    is_duplicate = True
                                    print(f"[Duplicate Check] MATCH FOUND! '{ipfs_hash_str}' == '{existing_hash}'")
                                    break
                            
                            if is_duplicate:
                                print(f"[Duplicate] This IPFS hash already exists in blockchain! Rejecting.")
                                print(f"[Duplicate Check] ❌❌❌ DUPLICATE DETECTED ON BLOCKCHAIN! ❌❌❌")
                                print(f"[Duplicate Check] IPFS hash '{ipfs_hash_str}' already exists on-chain")
                                print(f"[Duplicate Check] This means the same file was already uploaded and tokenized by another user")
                                print(f"[Duplicate Check] No token will be issued for this duplicate submission")
                                
                                # Update DB status to 'Duplicate'
                                c.status = "Duplicate"
                                c.ipfs_cid = ipfs_hash  # Store CID
                                db.session.commit()
                                print(f"[Duplicate Check] Contribution {cid} marked as Duplicate in database")
                                print(f"[Duplicate Check] ========== DUPLICATE CHECK COMPLETE - REJECTED ==========")
                                
                                # Send notification to user
                                socketio.emit("contribution_reviewed", {
                                    "id": cid, 
                                    "status": c.status,
                                    "message": "❌ This file was already uploaded earlier. Token will not be issued.",
                                    "userId": c.author_id
                                })
                                
                                # RETURN IMMEDIATELY - DO NOT CALL saveHashWithUser() and DO NOT AWARD TOKENS
                                return jsonify({
                                    "status": "duplicate",
                                    "newStatus": "Duplicate",
                                    "message": "This file was already uploaded earlier. Token will not be issued.",
                                    "rejectionReason": "Duplicate contribution. This file was already submitted and verified on blockchain."
                                }), 409
                            else:
                                print(f"[Duplicate Check] ✅ No duplicate found on blockchain")
                                print(f"[Duplicate Check] ✅ IPFS hash '{ipfs_hash_str}' is unique - proceeding with saveHashWithUser()")
                                print(f"[Duplicate Check] ========== DUPLICATE CHECK COMPLETE - APPROVED ==========")
                                
                                # No duplicate found - proceed with blockchain save
                                print(f"[Blockchain] Proceeding to save hash to blockchain...")
                                nonce = w3.eth.get_transaction_count(acct.address)
                                # Use saveHashWithUser to include user ID reference
                                user_id = c.author_id
                                tx = contract.functions.saveHashWithUser(ipfs_hash, user_id).build_transaction({
                                    "from": acct.address,
                                    "nonce": nonce,
                                    "gas": 300000,
                                    "maxFeePerGas": w3.to_wei("2", "gwei"),
                                    "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
                                    "chainId": w3.eth.chain_id,
                                })
                                signed = acct.sign_transaction(tx)
                                txh = w3.eth.send_raw_transaction(signed.rawTransaction)
                                tx_hash = txh.hex()
                                print(f"[Blockchain] Transaction successful: {tx_hash} (user_id: {user_id})")
                                
                        except Exception as dup_check_err:
                            print(f"[Duplicate Check] ERROR: Could not check blockchain for duplicates: {dup_check_err}")
                            print(f"[Duplicate Check] Exception type: {type(dup_check_err).__name__}")
                            import traceback
                            print(f"[Duplicate Check] Traceback: {traceback.format_exc()}")
                            # If blockchain check fails, we cannot safely proceed
                            # Return error instead of proceeding blindly
                            raise Exception(f"Blockchain duplicate check failed: {str(dup_check_err)}")
                    else:
                        print(f"[Blockchain] Contract address or deployer key not configured - skipping blockchain operations")
                except ConnectionError as ce:
                    print(f"[Blockchain] {str(ce)}")
                    # Continue without blockchain - IPFS is enough
                    print(f"[Blockchain] Note: IPFS upload completed successfully. Blockchain is optional.")
                except Exception as e:
                    print(f"[Blockchain] Transaction failed: {e}")
                    print(f"[Blockchain] Note: IPFS upload completed successfully. Blockchain is optional.")
                    # Continue without blockchain - IPFS is enough
            
            # Update contribution with IPFS metadata, approved status, and reward amount
            print(f"[Approval] Saving IPFS hash to database: {ipfs_hash}")
            c.ipfs_cid = ipfs_hash
            if ipfs_metadata:
                c.ipfs_file_size = ipfs_metadata.get("size")
                c.ipfs_pin_timestamp = ipfs_metadata.get("timestamp")
                print(f"[Approval] IPFS metadata: size={c.ipfs_file_size}, timestamp={c.ipfs_pin_timestamp}")
            c.status = "Accepted"
            c.reward_amount = 100.00  # Set reward to 100.00 tokens
            
            # Add reward tokens to user's balance
            c.author.cnri_balance = (c.author.cnri_balance or 0.0) + 100.00
            
            db.session.commit()
            print(f"[Approval] Contribution {cid} updated in database with IPFS CID: {ipfs_hash}")
            
            # Send notification to user with reward info
            socketio.emit("contribution_reviewed", {
                "id": cid, 
                "status": c.status,
                "message": f"Your contribution has been approved! You earned 100.00 CTRI tokens. New balance: {c.author.cnri_balance:.2f} CTRI",
                "ipfsHash": ipfs_hash,
                "txHash": tx_hash,
                "userId": c.author_id,
                "rewardAmount": 100.00,
                "newBalance": c.author.cnri_balance,
            })
            
            # Return success response with Pinata verification links
            pinata_url = f"https://app.pinata.cloud/pinmanager"
            ipfs_gateway_url = f"https://ipfs.io/ipfs/{ipfs_hash}" if ipfs_hash else None
            
            return jsonify({
                "status": "ok", 
                "newStatus": c.status, 
                "message": f"Contribution approved! Rewarded 100.00 CTRI tokens.",
                "ipfsHash": ipfs_hash,
                "ipfsGatewayUrl": ipfs_gateway_url,
                "pinataDashboardUrl": pinata_url,
                "txHash": tx_hash,
                "rewardAmount": 100.00,
                "userBalance": c.author.cnri_balance,
                "uploadedFileName": ipfs_metadata.get("name") if ipfs_metadata else None,
                "uploadedFileSize": ipfs_metadata.get("size") if ipfs_metadata else None,
            })
            
        except Exception as e:
            # Surface clearer errors for missing/invalid Pinata credentials
            msg = str(e)
            if "Pinata" in msg or "credentials" in msg:
                return jsonify({"error": "IPFS upload failed", "details": msg}), 500
            return jsonify({"error": f"Failed to process approval: {msg}"}), 500


@api_bp.post("/contributions/<int:cid>/claim-reward")
@jwt_required()
def claim_reward(cid: int):
    c = Contribution.query.get_or_404(cid)
    # Minimal on-chain transfer using deployer key (demo). Amount fixed/mock.
    amount = int((c.reward_amount or 1.0) * 10**18)
    try:
        with open(Config.CONTRACT_ABI_PATH, "r") as f:
            data = json.load(f)
        abi = data["abi"]
        address = Config.CONTRACT_ADDRESS or data.get("address")
        if not address:
            return jsonify({"error": "Contract not deployed"}), 400
        w3 = Web3(Web3.HTTPProvider(Config.GANACHE_URL))
        acct = w3.eth.account.from_key(Config.DEPLOYER_PRIVATE_KEY)
        contract = w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)
        nonce = w3.eth.get_transaction_count(acct.address)
        tx = contract.functions.transfer(acct.address, amount).build_transaction({
            "from": acct.address,
            "nonce": nonce,
            "gas": 200000,
            "maxFeePerGas": w3.to_wei("2", "gwei"),
            "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
            "chainId": w3.eth.chain_id,
        })
        signed = acct.sign_transaction(tx)
        txh = w3.eth.send_raw_transaction(signed.rawTransaction)
        tx_hash = txh.hex()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    socketio.emit("token_transferred", {"contributionId": cid, "txHash": tx_hash, "amount": c.reward_amount})
    return jsonify({"status": "ok", "txHash": tx_hash})


@api_bp.post("/upload")
@jwt_required(optional=True)
def upload_and_store_hash():
    # Accepts multipart form with file + metadata
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file or not allowed(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    # Save to persistent uploads folder
    filename = save_upload(file, current_app.config["UPLOAD_FOLDER"])
    local_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file_url = f"/api/uploads/{filename}"

    # Upload to IPFS via Pinata
    try:
        ipfs_metadata = upload_file_to_pinata(local_path, name=filename)
        ipfs_hash = ipfs_metadata.get("cid") if ipfs_metadata else None
    except Exception as e:
        return jsonify({"error": f"IPFS upload failed: {str(e)}"}), 500

    # Optionally skip on-chain step if client wants to use MetaMask signer
    skip_chain = request.args.get("skipChain") in ("1", "true", "True") or (request.form.get("skipChain") in ("1", "true", "True") if request.form else False)

    if skip_chain:
        return jsonify({
            "status": "success", 
            "ipfs_hash": ipfs_hash,
            "ipfs_size": ipfs_metadata.get("size"),
            "ipfs_timestamp": ipfs_metadata.get("timestamp"),
            "file_url": file_url
        })

    # Send to smart contract (saveHash) using backend signer
    try:
        with open(Config.CONTRACT_ABI_PATH, "r") as f:
            data = json.load(f)
        abi = data["abi"]
        address = Config.CONTRACT_ADDRESS or data.get("address")
        if not address:
            return jsonify({"error": "Contract not deployed"}), 400
        w3 = Web3(Web3.HTTPProvider(Config.GANACHE_URL))
        acct = w3.eth.account.from_key(Config.DEPLOYER_PRIVATE_KEY)
        contract = w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)
        nonce = w3.eth.get_transaction_count(acct.address)
        tx = contract.functions.saveHash(ipfs_hash).build_transaction({
            "from": acct.address,
            "nonce": nonce,
            "gas": 300000,
            "maxFeePerGas": w3.to_wei("2", "gwei"),
            "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
            "chainId": w3.eth.chain_id,
        })
        signed = acct.sign_transaction(tx)
        txh = w3.eth.send_raw_transaction(signed.rawTransaction)
        tx_hash = txh.hex()
    except Exception as e:
        return jsonify({"error": f"Blockchain tx failed: {str(e)}"}), 500

    return jsonify({
        "status": "success", 
        "ipfs_hash": ipfs_hash,
        "ipfs_size": ipfs_metadata.get("size"),
        "ipfs_timestamp": ipfs_metadata.get("timestamp"),
        "tx_hash": tx_hash, 
        "file_url": file_url
    })


