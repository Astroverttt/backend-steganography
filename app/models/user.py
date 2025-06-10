from sqlalchemy import Column, String, Boolean, UUID, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base
import uuid

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    artworks = relationship("Artwork", back_populates="owner") 
    receipts = relationship("Receipt", back_populates="buyer")
    
# class Artwork(Base): #Tambahkan Class Artwork
#     __tablename__ = "artworks"
#     id = Column(Integer, primary_key=True, index=True)
#     title = Column(String)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
#     owner = relationship("User", back_populates="artworks")