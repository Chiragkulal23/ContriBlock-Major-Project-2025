from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from backend.extensions import db
from backend.api import api_bp
from backend.models.user import User
from backend.models.kyc_document import KycDocument
from backend.services.storage import save_upload
import os


@api_bp.route("/kyc/upload", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def upload_kyc():
    """Upload KYC document. Allows upload if email is verified via OTP."""
    if request.method == "OPTIONS":
        return ("", 204)
    
    try:
        # Get verified email from form data first
        verified_email = request.form.get("verified_email", "").strip()
        print(f"[KYC Upload] Verified email from form: '{verified_email}'")
        print(f"[KYC Upload] All form keys: {list(request.form.keys())}")
        
        # Try to get user ID from JWT token first
        uid = get_jwt_identity()
        user = None
        
        if uid:
            try:
                uid = int(uid)
                user = User.query.get(uid)
                if user:
                    print(f"[KYC Upload] User from JWT: ID={uid}, Email={user.email}")
                else:
                    print(f"[KYC Upload] JWT user not found: ID={uid}")
            except Exception as e:
                print(f"[KYC Upload] JWT error: {e}")
                uid = None
        
        # If no user from JWT but email is verified, try to find user by email (case-insensitive)
        if not user and verified_email:
            # Try exact match first
            user = User.query.filter_by(email=verified_email).first()
            if not user:
                # Try case-insensitive lookup
                user = User.query.filter(func.lower(User.email) == func.lower(verified_email)).first()
            
            if user:
                uid = user.id
                print(f"[KYC Upload] User found by email: ID={uid}, Email={user.email}")
            else:
                print(f"[KYC Upload] No user found with email: '{verified_email}'")
                # List all user emails for debugging
                all_users = User.query.all()
                print(f"[KYC Upload] All user emails in DB: {[u.email for u in all_users]}")
        
        # If still no user, return error
        if not user:
            error_msg = f"User not found. Verified email: '{verified_email}'. Please make sure you're logged in with the same email."
            print(f"[KYC Upload] {error_msg}")
            return jsonify({"error": error_msg}), 401
        
        uid = user.id
        print(f"[KYC Upload] Processing upload for User ID: {uid}, Email: {user.email}")
        
        # Check if file is provided
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files["file"]
        if not file or not file.filename:
            return jsonify({"error": "Invalid file"}), 400
        
        # Check file extension
        allowed_ext = {"pdf", "png", "jpg", "jpeg"}
        ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
        if ext not in allowed_ext:
            return jsonify({"error": f"Invalid file type. Only PDF and images allowed. Got: {ext}"}), 400
        
        # Check file size (max 20MB)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        max_size = 20 * 1024 * 1024  # 20MB
        if file_size > max_size:
            return jsonify({"error": f"File too large. Maximum size is 20MB. Got: {file_size / 1024 / 1024:.2f}MB"}), 400
        
        # Use verified email from form data, or fallback to user's email
        if not verified_email:
            verified_email = user.email
        
        # Ensure upload folder exists
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file
        try:
            filename = save_upload(file, upload_folder)
            file_url = f"/api/uploads/{filename}"
        except Exception as e:
            print(f"[KYC Upload] Error saving file: {e}")
            return jsonify({"error": f"Failed to save file: {str(e)}"}), 500
        
        # Create or update KYC document
        kyc_doc = KycDocument.query.filter_by(user_id=uid).first()
        if not kyc_doc:
            kyc_doc = KycDocument(
                user_id=uid,
                file_url=file_url,
                status="Pending",
                verified_email=verified_email
            )
            db.session.add(kyc_doc)
        else:
            kyc_doc.file_url = file_url
            kyc_doc.status = "Pending"
            kyc_doc.verified_email = verified_email
        
        # Update user KYC status
        user.kyc_verified = False
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[KYC Upload] Database error: {e}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        
        return jsonify({
            "status": "success", 
            "message": "KYC document uploaded successfully", 
            "kyc": kyc_doc.to_dict()
        })
    except Exception as e:
        print(f"[KYC Upload] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@api_bp.route("/kyc/status", methods=["GET"])
@jwt_required()
def get_kyc_status():
    uid = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    kyc_doc = KycDocument.query.filter_by(user_id=uid).first()
    
    return jsonify({
        "kycVerified": bool(user.kyc_verified),
        "kycStatus": kyc_doc.status if kyc_doc else "None",
        "kycDocument": kyc_doc.to_dict() if kyc_doc else None
    })


@api_bp.route("/kyc/admin/list", methods=["GET"])
@jwt_required()
def list_kyc_requests():
    uid = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    if user.role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    
    # Get status filter from query params (default: all)
    status_filter = request.args.get("status")
    query = KycDocument.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    kyc_docs = query.order_by(KycDocument.created_at.desc()).all()
    return jsonify([doc.to_dict() for doc in kyc_docs])


@api_bp.route("/kyc/admin/approve/<int:kyc_id>", methods=["POST"])
@jwt_required()
def approve_kyc(kyc_id):
    uid = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    if user.role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    
    kyc_doc = KycDocument.query.get_or_404(kyc_id)
    kyc_doc.status = "Verified"
    kyc_doc.user.kyc_verified = True
    db.session.commit()
    
    return jsonify({"status": "success", "message": "KYC approved", "kyc": kyc_doc.to_dict()})


@api_bp.route("/kyc/admin/reject/<int:kyc_id>", methods=["POST"])
@jwt_required()
def reject_kyc(kyc_id):
    uid = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    if user.role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    
    kyc_doc = KycDocument.query.get_or_404(kyc_id)
    kyc_doc.status = "Rejected"
    kyc_doc.user.kyc_verified = False
    db.session.commit()
    
    return jsonify({"status": "success", "message": "KYC rejected", "kyc": kyc_doc.to_dict()})

