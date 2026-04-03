# Pseudo-code for MyContri Platform Functions

## Function: review_contribution(cid)
function review_contribution(cid):
    # Step 1: Verify admin authorization
    uid = get_jwt_identity()
    user = User.query.get(uid)
    if user.role != "admin":
        return error 403
    
    # Step 2: Validate action parameter
    action = request.get_json().get("action").lower()
    if action not in {"accept", "reject"}:
        return error 400
    
    # Step 3: Get contribution record
    c = Contribution.query.get_or_404(cid)
    
    # Step 4: Handle rejection
    if action == "reject":
        c.status = "Rejected"
        db.session.commit()
        emit notification to user
        return success response
    
    # Step 5: Handle acceptance - validate Pinata credentials
    if action == "accept":
        auth_status = test_pinata_auth()
        if not auth_status.get("ok"):
            return error 500
        
        # Step 6: Resolve local file path
        local_path = None
        if c.file_url:
            filename = os.path.basename(c.file_url)
            local_path = os.path.join(UPLOAD_FOLDER, filename)
            if not os.path.exists(local_path):
                local_path = None
        
        # Step 7: Pre-upload duplicate check (file hash comparison)
        if local_path and os.path.exists(local_path):
            file_hash = calculate_sha256(local_path)
            file_size = os.path.getsize(local_path)
            
            existing_same_size = Contribution.query.filter(
                ipfs_file_size == file_size,
                status == "Accepted",
                ipfs_cid is not None
            ).all()
            
            for existing in existing_same_size:
                existing_path = resolve_path(existing.file_url)
                if os.path.exists(existing_path):
                    existing_hash = calculate_sha256(existing_path)
                    if file_hash == existing_hash:
                        c.status = "Duplicate"
                        c.ipfs_cid = existing.ipfs_cid
                        db.session.commit()
                        emit notification
                        return duplicate error 409
        
        # Step 8: Upload to IPFS via Pinata
        ipfs_metadata = None
        ipfs_hash = None
        
        if local_path and os.path.exists(local_path):
            ipfs_metadata = upload_file_to_pinata(local_path, name=filename)
            ipfs_hash = ipfs_metadata.get("cid")
        else:
            create temporary text file with contribution details
            ipfs_metadata = upload_file_to_pinata(temp_file, name=title)
            ipfs_hash = ipfs_metadata.get("cid")
        
        # Step 9: Post-upload duplicate check (IPFS CID comparison)
        if ipfs_hash:
            existing_contribution = Contribution.query.filter_by(
                ipfs_cid=ipfs_hash,
                status="Accepted"
            ).first()
            if existing_contribution:
                c.status = "Duplicate"
                c.ipfs_cid = ipfs_hash
                db.session.commit()
                emit notification
                return duplicate error 409
        
        # Step 10: Blockchain duplicate check
        if ipfs_hash:
            w3 = Web3(HTTPProvider(GANACHE_URL))
            contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)
            existing_hashes = contract.functions.getAllHashes().call()
            
            for existing_hash in existing_hashes:
                if str(ipfs_hash).strip() == str(existing_hash).strip():
                    c.status = "Duplicate"
                    c.ipfs_cid = ipfs_hash
                    db.session.commit()
                    emit notification
                    return duplicate error 409
        
        # Step 11: Save hash to blockchain
        if ipfs_hash and no duplicate found:
            nonce = w3.eth.get_transaction_count(account.address)
            tx = contract.functions.saveHashWithUser(ipfs_hash, user_id).build_transaction({
                from: account.address,
                nonce: nonce,
                gas: 300000
            })
            signed = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        
        # Step 12: Update contribution status and reward
        c.ipfs_cid = ipfs_hash
        c.ipfs_file_size = ipfs_metadata.get("size")
        c.ipfs_pin_timestamp = ipfs_metadata.get("timestamp")
        c.status = "Accepted"
        c.reward_amount = 100.00
        c.author.cnri_balance += 100.00
        db.session.commit()
        
        # Step 13: Send success notification
        emit notification with reward info
        return success response with IPFS details


## Function: create_contribution()
function create_contribution():
    # Step 1: Get authenticated user
    uid = get_jwt_identity()
    user = User.query.get(uid)
    
    # Step 2: Handle optional file upload
    file_url = None
    if "file" in request.files:
        file = request.files["file"]
        if file and allowed(file.filename):
            filename = save_upload(file, UPLOAD_FOLDER)
            file_url = f"/api/uploads/{filename}"
    
    # Step 3: Extract form data
    title = request.form.get("title") or "Untitled"
    description = request.form.get("description") or ""
    
    # Step 4: Create contribution record
    contrib = Contribution(
        title=title,
        description=description,
        author=user,
        ipfs_cid=None,
        file_url=file_url,
        reward_amount=0.0,
        status="Pending"
    )
    db.session.add(contrib)
    db.session.commit()
    
    # Step 5: Emit real-time notification
    socketio.emit("new_contribution", contrib.to_card())
    return contrib details


## Function: upload_kyc()
function upload_kyc():
    # Step 1: Get verified email from form
    verified_email = request.form.get("verified_email").strip()
    
    # Step 2: Get user from JWT or email lookup
    uid = get_jwt_identity()
    user = None
    if uid:
        user = User.query.get(int(uid))
    
    if not user and verified_email:
        user = User.query.filter_by(email=verified_email).first()
    
    if not user:
        return error 401
    
    # Step 3: Validate file presence
    if "file" not in request.files:
        return error 400
    
    file = request.files["file"]
    if not file or not file.filename:
        return error 400
    
    # Step 4: Validate file extension
    ext = file.filename.rsplit(".", 1)[1].lower()
    allowed_ext = {"pdf", "png", "jpg", "jpeg"}
    if ext not in allowed_ext:
        return error 400
    
    # Step 5: Validate file size (max 20MB)
    file.seek(0, SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 20MB:
        return error 400
    
    # Step 6: Save file to upload folder
    filename = save_upload(file, UPLOAD_FOLDER)
    file_url = f"/api/uploads/{filename}"
    
    # Step 7: Create or update KYC document
    kyc_doc = KycDocument.query.filter_by(user_id=user.id).first()
    if not kyc_doc:
        kyc_doc = KycDocument(
            user_id=user.id,
            file_url=file_url,
            status="Pending",
            verified_email=verified_email
        )
        db.session.add(kyc_doc)
    else:
        kyc_doc.file_url = file_url
        kyc_doc.status = "Pending"
        kyc_doc.verified_email = verified_email
    
    # Step 8: Update user KYC status
    user.kyc_verified = False
    db.session.commit()
    
    return success response with KYC details


## Function: upload_file_to_pinata(path, name)
function upload_file_to_pinata(path, name):
    # Step 1: Validate Pinata credentials
    api_key = Config.PINATA_API_KEY
    api_secret = Config.PINATA_SECRET_API_KEY
    if not api_key or not api_secret:
        raise error "Missing Pinata credentials"
    
    # Step 2: Validate file exists
    if not os.path.exists(path):
        raise FileNotFoundError
    
    # Step 3: Prepare upload request
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        pinata_api_key: api_key,
        pinata_secret_api_key: api_secret
    }
    pinata_filename = name or os.path.basename(path)
    metadata = {name: pinata_filename}
    
    # Step 4: Retry upload with exponential backoff (3 attempts)
    for attempt in range(3):
        try:
            with open(path, "rb") as file_obj:
                files = {file: (pinata_filename, file_obj)}
                data = {pinataMetadata: json.dumps(metadata)}
                response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
                
                if response.status_code >= 500 or response.status_code == 429:
                    raise RuntimeError
                
                response.raise_for_status()
                response_data = response.json()
                
                # Step 5: Extract IPFS metadata
                cid = response_data.get("IpfsHash") or response_data.get("ipfsHash")
                if not cid:
                    raise RuntimeError
                
                result = {
                    cid: cid,
                    size: response_data.get("PinSize"),
                    timestamp: response_data.get("Timestamp"),
                    name: pinata_filename
                }
                return result
        except Exception as e:
            if attempt < 2:
                wait_time = 0.5 + attempt
                time.sleep(wait_time)
                continue
            raise RuntimeError
    
    raise RuntimeError "Upload failed after 3 attempts"


## Function: register()
function register():
    # Step 1: Extract registration data
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")
    
    # Step 2: Validate required fields
    if not all([name, email, password]):
        return error 400
    
    # Step 3: Check if email already exists
    if User.query.filter_by(email=email).first():
        return error 400 "Email already registered"
    
    # Step 4: Create new user
    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    # Step 5: Generate JWT token
    token = create_access_token(identity=str(user.id))
    return {token: token, user: user.to_dict()}


## Function: login()
function login():
    # Step 1: Extract credentials
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    
    # Step 2: Find user by email
    user = User.query.filter_by(email=email).first()
    
    # Step 3: Verify password
    if not user or not user.check_password(password):
        return error 401 "Invalid credentials"
    
    # Step 4: Generate JWT token
    token = create_access_token(identity=str(user.id))
    return {token: token, user: user.to_dict()}


## Function: approve_kyc(kyc_id)
function approve_kyc(kyc_id):
    # Step 1: Verify admin authorization
    uid = get_jwt_identity()
    user = User.query.get(uid)
    if user.role != "admin":
        return error 403
    
    # Step 2: Get KYC document
    kyc_doc = KycDocument.query.get_or_404(kyc_id)
    
    # Step 3: Update KYC status
    kyc_doc.status = "Verified"
    kyc_doc.user.kyc_verified = True
    db.session.commit()
    
    return success response with KYC details


## Function: reject_kyc(kyc_id)
function reject_kyc(kyc_id):
    # Step 1: Verify admin authorization
    uid = get_jwt_identity()
    user = User.query.get(uid)
    if user.role != "admin":
        return error 403
    
    # Step 2: Get KYC document
    kyc_doc = KycDocument.query.get_or_404(kyc_id)
    
    # Step 3: Update KYC status
    kyc_doc.status = "Rejected"
    kyc_doc.user.kyc_verified = False
    db.session.commit()
    
    return success response with KYC details


## Function: claim_reward(cid)
function claim_reward(cid):
    # Step 1: Get contribution
    c = Contribution.query.get_or_404(cid)
    
    # Step 2: Calculate token amount
    amount = int((c.reward_amount or 1.0) * 10^18)
    
    # Step 3: Load contract ABI and address
    with open(CONTRACT_ABI_PATH) as f:
        data = json.load(f)
    abi = data["abi"]
    address = CONTRACT_ADDRESS or data.get("address")
    
    # Step 4: Connect to blockchain
    w3 = Web3(HTTPProvider(GANACHE_URL))
    account = w3.eth.account.from_key(DEPLOYER_PRIVATE_KEY)
    contract = w3.eth.contract(address=address, abi=abi)
    
    # Step 5: Build and send transaction
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.functions.transfer(account.address, amount).build_transaction({
        from: account.address,
        nonce: nonce,
        gas: 200000
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    
    # Step 6: Emit notification
    socketio.emit("token_transferred", {contributionId: cid, txHash: tx_hash})
    return success response with tx_hash

