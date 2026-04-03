from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.extensions import db
from backend.api import api_bp
from backend.models.user import User
from backend.services.storage import save_upload
import os
import random


@api_bp.get("/profile/<int:user_id>")
def get_profile(user_id: int):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@api_bp.put("/profile/<int:user_id>")
@jwt_required()
def update_profile(user_id: int):
    uid = int(get_jwt_identity())
    if uid != user_id:
        return jsonify({"error": "Forbidden"}), 403
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    user.name = data.get("name", user.name)
    user.avatar_url = data.get("avatarUrl", user.avatar_url)
    user.bio = data.get("bio", user.bio)
    db.session.commit()
    return jsonify(user.to_dict())


# --- KYC (Aadhaar mock) ---

@api_bp.route("/profile/kyc/start", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def kyc_start():
    if request.method == "OPTIONS":
        return ("", 204)
    uid = get_jwt_identity()
    if uid is None:
        return jsonify({"error": "Unauthorized"}), 401
    uid = int(uid)
    user = User.query.get_or_404(uid)
    data = request.get_json() or {}
    aadhaar = (data.get("aadhaar") or "").strip()
    if not aadhaar.isdigit() or len(aadhaar) not in (12,):
        return jsonify({"error": "Invalid Aadhaar number"}), 400

    # Mock OTP generation and store in server-side session-like memory (simple demo)
    otp = str(random.randint(100000, 999999))
    # For demo, keep OTP in user.bio temporarily to avoid adding a table. Real app should use Redis/DB.
    marker = "__KYC_OTP__"
    user.bio = (user.bio or "")
    # Remove old marker
    user.bio = "\n".join(line for line in user.bio.splitlines() if not line.startswith(marker))
    user.bio += f"\n{marker}:{otp}"
    db.session.commit()

    # Do not expose full Aadhaar
    last4 = aadhaar[-4:]
    return jsonify({"status": "otp_sent", "mask": f"********{last4}"})


@api_bp.route("/profile/kyc/verify", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def kyc_verify():
    if request.method == "OPTIONS":
        return ("", 204)
    uid = get_jwt_identity()
    if uid is None:
        return jsonify({"error": "Unauthorized"}), 401
    uid = int(uid)
    user = User.query.get_or_404(uid)
    data = request.get_json() or {}
    otp = (data.get("otp") or "").strip()
    aadhaar = (data.get("aadhaar") or "").strip()

    marker = "__KYC_OTP__"
    current_otp = None
    for line in (user.bio or "").splitlines():
        if line.startswith(marker + ":"):
            current_otp = line.split(":", 1)[1].strip()
            break

    if not current_otp or otp != current_otp:
        return jsonify({"error": "Invalid or expired OTP"}), 400

    # Mark verified
    user.kyc_verified = True
    user.kyc_aadhaar_last4 = aadhaar[-4:] if aadhaar else user.kyc_aadhaar_last4
    # Remove OTP marker
    user.bio = "\n".join(line for line in (user.bio or "").splitlines() if not line.startswith(marker))
    db.session.commit()

    return jsonify({"status": "verified", "user": user.to_dict()})


# --- Profile photo upload ---

@api_bp.route("/profile/avatar", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def upload_avatar():
    if request.method == "OPTIONS":
        return ("", 204)
    uid = get_jwt_identity()
    if uid is None:
        return jsonify({"error": "Unauthorized"}), 401
    uid = int(uid)
    user = User.query.get_or_404(uid)
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "Invalid file"}), 400

    filename = save_upload(file, current_app.config["UPLOAD_FOLDER"])
    user.avatar_url = f"/api/uploads/{filename}"
    db.session.commit()
    return jsonify({"status": "ok", "avatarUrl": user.avatar_url})

