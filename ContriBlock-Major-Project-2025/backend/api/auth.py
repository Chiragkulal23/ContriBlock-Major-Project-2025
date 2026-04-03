from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from backend.extensions import db
from backend.api import api_bp
from backend.models.user import User


@api_bp.post("/auth/register")
def register():
    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")
    if not all([name, email, password]):
        return jsonify({"error": "Missing fields"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400
    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": user.to_dict()})


@api_bp.post("/auth/login")
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password or ""):
        return jsonify({"error": "Invalid credentials"}), 401
    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": user.to_dict()})


@api_bp.get("/auth/me")
@jwt_required()
def me():
    uid = get_jwt_identity()
    user = User.query.get(int(uid))
    return jsonify(user.to_dict())


