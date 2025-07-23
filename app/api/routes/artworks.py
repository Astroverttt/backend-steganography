from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.database import get_db
from app.models.artwork import Artwork
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/{artwork_id}")
def get_artwork_detail(artwork_id: UUID, db: Session = Depends(get_db)):
    logger.info(f"Backend received request for artwork ID: {artwork_id}")
    artwork = db.query(Artwork).filter(Artwork.id == artwork_id).first()

    if not artwork:
        logger.warning(f"Backend: Artwork with ID {artwork_id} NOT FOUND in database.")
        raise HTTPException(status_code=404, detail="Artwork tidak ditemukan")

    logger.info(f"Backend: Artwork {artwork_id} found: {artwork.title}")
    return {
        "id": str(artwork.id),
        "title": artwork.title,
        "description": artwork.description,
        "image_url": artwork.image_url, 
        "username": artwork.owner.username,
        "name": artwork.owner.name,
        "profile_picture": artwork.owner.profile_picture
    }
