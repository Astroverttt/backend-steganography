from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base

class Purchase(Base):
    __tablename__ = "purchases"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    artwork_id = Column(UUID(as_uuid=True), ForeignKey("artworks.id"), primary_key=True)

    user = relationship("User", back_populates="purchases")
    artwork = relationship("Artwork", back_populates="purchases")
