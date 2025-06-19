from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.models.like import Like
from app.models.artwork import Artwork
from app.api.deps import get_current_user
from app.schemas.like_schema import LikeResponse
from uuid import UUID

router = APIRouter()

@router.post("/{artwork_id}", status_code=200)
def toggle_like(
    artwork_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    artwork = db.query(Artwork).filter(Artwork.id == artwork_id).first()
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")

    existing_like = db.query(Like).filter_by(user_id=current_user.id, artwork_id=artwork_id).first()

    if existing_like:
        db.delete(existing_like)
        db.commit()
        return {"message": "Unliked the artwork"}
    else:
        new_like = Like(user_id=current_user.id, artwork_id=artwork_id)
        db.add(new_like)
        db.commit()
        return {"message": "Liked the artwork"}

@router.get("/me", response_model=list[LikeResponse])
def get_my_likes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    likes = db.query(Like).filter_by(user_id=current_user.id).all()
    return likes
