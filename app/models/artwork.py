from sqlalchemy import (
    Column, UUID, String, Numeric, DateTime, func, ForeignKey, Text, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from app.db.database import Base 
import uuid
import os
import re
import hashlib

def clean_filename_part(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]', '', text.replace(" ", "_"))

def generate_unique_key(title, username, filename):
    _, ext = os.path.splitext(filename) 
    title_clean = clean_filename_part(title)
    username_clean = clean_filename_part(username)
    unique_id = str(uuid.uuid4())[:8]

    return f"{unique_id}_{title_clean}_{username_clean}{ext}"


class Artwork(Base):
    __tablename__ = "artworks"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, index=True, nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False, default=0.00)

    owner_id = Column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    artwork_secret_code = Column(String(8), unique=False, nullable=True, index=True)

    category = Column(String(255), nullable=True)
    license_type = Column(
        String,
        CheckConstraint("license_type IN ('FREE', 'BUY')"),
        nullable=True
    )

    image_url = Column(Text, nullable=False)
    unique_key = Column(String(255), unique=True, nullable=False)

    hash = Column(Text, nullable=False)
    hash_phash = Column(String, nullable=True)
    hash_dhash = Column(String, nullable=True)
    hash_whash = Column(String, nullable=True)

    owner = relationship("User", back_populates="artworks")
    receipts = relationship("Receipt", back_populates="artwork")
    likes = relationship("Like", back_populates="artwork", cascade="all, delete")
