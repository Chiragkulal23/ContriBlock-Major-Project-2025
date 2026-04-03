from backend.extensions import db
from backend.models import BaseModel


class TokenTransfer(BaseModel):
    __tablename__ = "token_transfers"
    sender = db.Column(db.String(64), nullable=False)
    recipient = db.Column(db.String(64), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tx_hash = db.Column(db.String(80))


