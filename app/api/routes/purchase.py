from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.database import get_db
from app.models.user import User
from app.models.artwork import Artwork
from app.models.purchase import Purchase
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/purchase/{artwork_id}")
def purchase_artwork(
    artwork_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    artwork = db.query(Artwork).filter(Artwork.id == artwork_id).first()
    if not artwork:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artwork tidak ditemukan"
        )

    if artwork.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kamu tidak bisa membeli karya milikmu sendiri"
        )

    if artwork.is_sold:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Artwork sudah terjual"
        )

    existing_purchase = db.query(Purchase).filter_by(
        user_id=current_user.id,
        artwork_id=artwork_id
    ).first()
    if existing_purchase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kamu sudah membeli karya ini"
        )

    new_purchase = Purchase(user_id=current_user.id, artwork_id=artwork_id)
    db.add(new_purchase)

    artwork.is_sold = True
    db.commit()

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Pembelian berhasil",
            "artwork": {
                "id": str(artwork.id),
                "title": artwork.title,
                "price": artwork.price,
                "is_sold": artwork.is_sold
            }
        }
    )
