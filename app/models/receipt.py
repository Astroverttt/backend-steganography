from sqlalchemy import Column, UUID, ForeignKey, Numeric, DateTime, func, String
from sqlalchemy.orm import relationship
from app.db.database import Base
import uuid

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    artwork_id = Column(UUID(as_uuid=True), ForeignKey("artworks.id", ondelete="CASCADE"), nullable=False)
    purchase_date = Column(DateTime, server_default=func.now())
    amount = Column(Numeric(10, 2), nullable=False)
    buyer_secret_code = Column(String(50), nullable=True)

    order_id = Column(String(255), nullable=True)
    transaction_id = Column(String(255), nullable=True)
    payment_type = Column(String(255), nullable=True)

    buyer = relationship("User", back_populates="receipts")
    artwork = relationship("Artwork", back_populates="receipts")