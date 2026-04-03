from backend.extensions import db
from backend.models import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash


class User(BaseModel):
    __tablename__ = "users"
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="user")
    avatar_url = db.Column(db.String(500))
    bio = db.Column(db.Text)
    cnri_balance = db.Column(db.Float, default=0.0)  # CTRI token balance (using existing column)
    # KYC fields (add a migration in real usage)
    kyc_verified = db.Column(db.Boolean, default=False)
    kyc_aadhaar_last4 = db.Column(db.String(4))

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id, 
            "name": self.name, 
            "email": self.email, 
            "role": self.role, 
            "avatarUrl": self.avatar_url, 
            "bio": self.bio,
            "ctriBalance": self.cnri_balance,
            "kycVerified": bool(self.kyc_verified),
            "kycAadhaarLast4": self.kyc_aadhaar_last4
        }


