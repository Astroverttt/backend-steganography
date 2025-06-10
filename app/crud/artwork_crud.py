from sqlalchemy.orm import Session
from app.models.artwork import Artwork
from app.models.user import User

def fet_all_artworks(
        db: Session,
        username: str = None,
        category: str = None,
        license_type: str = None
):
    query = db.query(Artwork)
    if username:
        query = query.join(User).filter(User.username.ilike(f"%{username}%"))
    if category:
        query = query.filter(Artwork.category.ilike(f"%{category}%"))
    if license_type:
        query = query.filter(Artwork.license_type.ilike(f"%{license_type}%"))
    return query.all()