from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.artwork import Artwork
from app.schemas.artwork_schema import ArtworkResponse
from typing import Optional, List

router = APIRouter()

@router.get("/explore", response_model=dict)
def explore_items(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=0),
    category: Optional[str] = None,
    query: Optional[str] = None
):
    artworks_query = db.query(Artwork)
    if category:
        artworks_query = artworks_query.filter(Artwork.category == category)
    if query:
        artworks_query = artworks_query.filter(Artwork.title.ilike(f"%{query}%"))

    artworks = artworks_query.offset(skip).limit(limit).all()

    if not artworks:
        return{
            "status": "success",
            "message": "Artworks not found.",\
            "result": [],
            "total": 0
        }
    
    return{
        "status": "success",
        "message": "Artworks found.",
        "result": artworks,
        "total": len(artworks)
    }