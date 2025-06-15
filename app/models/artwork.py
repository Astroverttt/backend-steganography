from sqlalchemy import Column, UUID, String, Numeric, DateTime, func, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.database import Base 
import uuid
import hashlib 

def generate_unique_key(user_id, filename):
    combined = f"{uuid.uuid4()}_{user_id}_{filename}"
    return hashlib.sha256(combined.encode()).hexdigest()

class Artwork(Base):
    __tablename__ = "artworks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, index=True, nullable=False) 
    description = Column(Text) 
    price = Column(Numeric(10, 2), nullable=False, default=0.00)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    category = Column(String(255), nullable=True) 
    license_type = Column(String, CheckConstraint("license_type IN ('FREE', 'BUY')"), nullable=True)
    image_url = Column(Text, nullable=False) 
    unique_key = Column(String(255), unique=True, nullable=False) 
    hash = Column(Text, nullable=False) 
    hash_phash = Column(String, nullable=True)
    hash_dhash = Column(String, nullable=True)
    hash_whash = Column(String, nullable=True)
    owner = relationship("User", back_populates="artworks")
    receipts = relationship("Receipt", back_populates="artwork")
