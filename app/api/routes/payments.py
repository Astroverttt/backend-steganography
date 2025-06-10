from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.models.artwork import Artwork
from app.models.receipt import Receipt
from app.api.deps import get_current_user
from pydantic import BaseModel

router = APIRouter()

class PurchaseRequest(BaseModel):
    artwork_id: str

@router.post("/purchase")
async def purchase_artwork(
    purchase_request: PurchaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    API untuk melakukan pembelian karya seni.
    """
    artwork = db.query(Artwork).filter(Artwork.id == purchase_request.artwork_id).first()
    if not artwork:
        raise HTTPException(status_code=404, detail="Karya seni tidak ditemukan")


    receipt = Receipt(
        buyer_id=current_user.id,
        artwork_id=artwork.id,
        amount=artwork.price
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    return {"message": f"Pembelian '{artwork.title}' berhasil!", "receipt_id": receipt.id}