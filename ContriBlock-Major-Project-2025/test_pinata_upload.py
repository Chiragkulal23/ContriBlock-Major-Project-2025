#!/usr/bin/env python3
"""
Simple test script to verify Pinata upload is working.
Run this from the project root directory.
"""
import os
import sys
import requests
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir.parent))

from backend.config import Config
from backend.services.storage import upload_file_to_pinata, test_pinata_auth

def main():
    print("=" * 60)
    print("Pinata Upload Test")
    print("=" * 60)
    
    # Test 1: Check credentials
    print("\n1. Testing Pinata authentication...")
    auth_status = test_pinata_auth()
    if not auth_status.get("ok"):
        print(f"❌ Authentication failed: {auth_status}")
        print("\nPlease check your PINATA_API_KEY and PINATA_SECRET_API_KEY in backend/.env")
        return 1
    print("✅ Authentication successful!")
    
    # Test 2: Find a test file
    print("\n2. Looking for test file...")
    upload_folder = Config.UPLOAD_FOLDER
    test_files = []
    
    if os.path.exists(upload_folder):
        for file in os.listdir(upload_folder):
            file_path = os.path.join(upload_folder, file)
            if os.path.isfile(file_path):
                test_files.append(file_path)
    
    if not test_files:
        print("❌ No files found in upload folder. Creating a test file...")
        test_file = os.path.join(upload_folder, "test_pinata_upload.txt")
        os.makedirs(upload_folder, exist_ok=True)
        with open(test_file, "w") as f:
            f.write("This is a test file for Pinata upload verification.\n")
            f.write(f"Created at: {os.path.basename(test_file)}\n")
        test_files.append(test_file)
    
    test_file = test_files[0]
    print(f"✅ Using test file: {test_file}")
    print(f"   File size: {os.path.getsize(test_file)} bytes")
    
    # Test 3: Upload to Pinata
    print("\n3. Uploading to Pinata...")
    try:
        result = upload_file_to_pinata(test_file, name="test_upload_verification")
        cid = result.get("cid")
        print(f"\n✅ Upload successful!")
        print(f"   CID: {cid}")
        print(f"   Size: {result.get('size')} bytes")
        print(f"   Timestamp: {result.get('timestamp')}")
        print(f"\n   View on IPFS gateway: https://ipfs.io/ipfs/{cid}")
        print(f"   Check Pinata dashboard: https://app.pinata.cloud/pinmanager")
        print("\n✅ Pinata upload is working correctly!")
        return 0
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        print("\nPlease check:")
        print("  1. Your Pinata API credentials in backend/.env")
        print("  2. Your internet connection")
        print("  3. Pinata service status")
        return 1

if __name__ == "__main__":
    sys.exit(main())

