from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.artwork import Artwork
from app.schemas.artwork_schema import ArtworkListResponse

router = APIRouter()

@router.get("/users/me/artworks", response_model=ArtworkListResponse)
def get_my_artworks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    artworks = db.query(Artwork).filter(Artwork.owner_id == current_user.id).all()

    return {
        "status": "success",
        "message": "Your artworks retrieved successfully." if artworks else "No artworks found.",
        "result": artworks,
        "total": len(artworks),
    }
