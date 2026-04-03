from backend.extensions import db
from backend.models import BaseModel


class Purchase(BaseModel):
    __tablename__ = "purchases"
    
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    contribution_id = db.Column(db.Integer, db.ForeignKey("contributions.id"), nullable=False)
    purchase_price = db.Column(db.Float, nullable=False, default=100.0)
    transaction_hash = db.Column(db.String(128), nullable=True)
    
    # Relationships
    user = db.relationship("User", backref="purchases")
    contribution = db.relationship("Contribution", backref="purchases")
    
    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "contributionId": self.contribution_id,
            "purchasePrice": self.purchase_price,
            "transactionHash": self.transaction_hash,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "contribution": self.contribution.to_card() if self.contribution else None
        }