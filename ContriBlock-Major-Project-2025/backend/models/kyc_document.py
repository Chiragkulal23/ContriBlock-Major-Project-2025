from backend.extensions import db
from backend.models import BaseModel


class KycDocument(BaseModel):
    __tablename__ = "kyc_documents"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    file_url = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), default="Pending")  # Pending, Verified, Rejected
    verified_email = db.Column(db.String(255))  # Email verified via OTP
    
    user = db.relationship("User", backref="kyc_document")
    
    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "userName": self.user.name if self.user else "Unknown",
            "userEmail": self.user.email if self.user else "Unknown",
            "fileUrl": self.file_url,
            "status": self.status,
            "verifiedEmail": self.verified_email,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }

