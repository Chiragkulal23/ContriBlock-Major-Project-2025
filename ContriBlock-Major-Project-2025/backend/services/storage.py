import os
import json
import hashlib
from typing import Optional, Dict, Any
import requests
from werkzeug.utils import secure_filename
from backend.config import Config


def calculate_ipfs_hash(file_path: str) -> str:
    """Calculate IPFS hash locally using the same algorithm as IPFS (CIDv0)."""
    # IPFS uses multihash format: <hash-function><digest-length><digest>
    # For IPFS CIDv0, it uses sha2-256 (0x12) with 32-byte digest (0x20)
    
    with open(file_path, 'rb') as f:
        # Read file in chunks to handle large files
        hasher = hashlib.sha256()
        while chunk := f.read(65536):  # 64KB chunks
            hasher.update(chunk)
        
        digest = hasher.digest()
        
        # Create multihash: sha2-256 (0x12) + 32 bytes (0x20) + digest
        multihash = b'\x12\x20' + digest
        
        # Encode to base58 (IPFS CIDv0 format)
        import base58
        cid = base58.b58encode(multihash).decode('ascii')
        
        return cid


def save_upload(file, upload_dir: str) -> str:
    os.makedirs(upload_dir, exist_ok=True)
    fname = secure_filename(file.filename)
    path = os.path.join(upload_dir, fname)
    file.save(path)
    return fname


def upload_file_to_pinata(path: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Upload a local file path to Pinata and return IPFS metadata (CID, size, timestamp)."""
    api_key = Config.PINATA_API_KEY
    api_secret = Config.PINATA_SECRET_API_KEY
    if not api_key or not api_secret:
        raise RuntimeError("Missing Pinata API credentials")

    print(f"[Pinata] Starting upload: {path} (name: {name})")
    print(f"[Pinata] API Key present: {bool(api_key)}, Secret present: {bool(api_secret)}")
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    
    file_size = os.path.getsize(path)
    print(f"[Pinata] File size: {file_size} bytes")

    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": api_key,
        "pinata_secret_api_key": api_secret,
    }
    
    # Prepare metadata with the desired filename
    pinata_filename = name or os.path.basename(path)
    pinata_metadata = {
        "name": pinata_filename
    }
    
    # Simple retry with backoff for transient failures/rate limits
    last_exc: Optional[Exception] = None
    for attempt in range(3):
        try:
            # Open file fresh for each attempt
            with open(path, "rb") as file_obj:
                files = {"file": (pinata_filename, file_obj)}
                data = {"pinataMetadata": json.dumps(pinata_metadata)}
                print(f"[Pinata] Attempt {attempt + 1}/3: Uploading to Pinata with filename: {pinata_filename}...")
                resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
                print(f"[Pinata] Response status: {resp.status_code}")
                
                if resp.status_code >= 500 or resp.status_code in (429,):
                    raise RuntimeError(f"Pinata transient error {resp.status_code}: {resp.text[:200]}")
                
                resp.raise_for_status()
                data = resp.json()
                print(f"[Pinata] Upload successful! Response: {data}")
                
                cid = data.get("IpfsHash") or data.get("ipfsHash")
                if not cid:
                    raise RuntimeError(f"No CID in Pinata response: {data}")
                
                result = {
                    "cid": cid,
                    "size": data.get("PinSize"),
                    "timestamp": data.get("Timestamp"),
                    "name": name or os.path.basename(path)
                }
                print(f"[Pinata] Upload complete! CID: {cid}, Size: {result.get('size')}, Timestamp: {result.get('timestamp')}")
                return result
        except Exception as e:
            last_exc = e
            print(f"[Pinata] Attempt {attempt + 1}/3 failed: {str(e)}")
            if attempt < 2:
                # Exponential backoff: 0.5s, 1.5s
                import time
                wait_time = 0.5 + attempt
                print(f"[Pinata] Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            print(f"[Pinata] All attempts failed. Last error: {str(e)}")
            raise RuntimeError(f"Pinata upload failed after 3 attempts: {str(e)}")


def check_ipfs_hash_exists(ipfs_hash: str) -> Dict[str, Any]:
    """Check if an IPFS hash already exists in Pinata for duplicate detection."""
    api_key = Config.PINATA_API_KEY
    api_secret = Config.PINATA_SECRET_API_KEY
    if not api_key or not api_secret:
        return {
            "ok": False,
            "reason": "Missing Pinata API credentials",
        }

    url = f"https://api.pinata.cloud/data/pinList?hashContains={ipfs_hash}&status=pinned"
    headers = {
        "pinata_api_key": api_key,
        "pinata_secret_api_key": api_secret,
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            # Check if any pins match our hash exactly
            pins = data.get("rows", [])
            exact_match = any(pin.get("ipfs_pin_hash") == ipfs_hash for pin in pins)
            return {
                "ok": True,
                "exists": exact_match,
                "count": len(pins),
                "pins": pins if exact_match else []
            }
        return {"ok": False, "status": resp.status_code, "body": resp.text[:500]}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def test_pinata_auth() -> Dict[str, Any]:
    """Test Pinata credentials using the official auth endpoint."""
    api_key = Config.PINATA_API_KEY
    api_secret = Config.PINATA_SECRET_API_KEY
    ok = bool(api_key and api_secret)
    if not ok:
        return {
            "ok": False,
            "reason": "Missing Pinata API credentials",
        }

    url = "https://api.pinata.cloud/data/testAuthentication"
    headers = {
        "pinata_api_key": api_key,
        "pinata_secret_api_key": api_secret,
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            return {"ok": True}
        return {"ok": False, "status": resp.status_code, "body": resp.text[:500]}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


