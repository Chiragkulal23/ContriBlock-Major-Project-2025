import os


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET", "jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES = False  # No expiration for dev
    JWT_TOKEN_LOCATION = ["headers"]  # Look for token in Authorization header
    UPLOAD_FOLDER = os.path.abspath(os.getenv("UPLOAD_FOLDER", os.path.join(os.path.dirname(__file__), "uploads")))
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    GANACHE_URL = os.getenv("GANACHE_URL", "http://127.0.0.1:7545")
    DEPLOYER_PRIVATE_KEY = os.getenv("DEPLOYER_PRIVATE_KEY", "")
    CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")
    CONTRACT_ABI_PATH = os.getenv("CONTRACT_ABI_PATH", os.path.join(os.path.dirname(__file__), "contracts", "build", "contract.json"))
    PINATA_API_KEY = os.getenv("PINATA_API_KEY", "")
    PINATA_SECRET_API_KEY = os.getenv("PINATA_SECRET_API_KEY", "")
    # EmailJS is used for OTP emails (client-side)
    # Mongo removed; using SQLAlchemy only


