from sqlalchemy import Column, UUID, ForeignKey, Numeric, DateTime, func, String
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLAEnum
import enum
from app.db.database import Base
import uuid

class ReceiptStatusEnum(enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    cancelled = "cancelled"
    expired = "expired" 

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    artwork_id = Column(UUID(as_uuid=True), ForeignKey("artworks.id", ondelete="CASCADE"), nullable=False)
    purchase_date = Column(DateTime, server_default=func.now())
    amount = Column(Numeric(10, 2), nullable=False)
    buyer_secret_code = Column(String, nullable=True)

    order_id = Column(String, nullable=True)
    transaction_id = Column(String, nullable=True)
    payment_type = Column(String, nullable=True)

    status = Column(SQLAEnum(ReceiptStatusEnum, name="receipt_status_enum"), 
                    default=ReceiptStatusEnum.pending, 
                    nullable=False)

    buyer = relationship("User", back_populates="receipts")
    artwork = relationship("Artwork", back_populates="receipts")

    def __repr__(self):
        return f"<Receipt {self.id} (Order: {self.order_id}, Status: {self.status.value})>" 