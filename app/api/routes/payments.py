from fastapi import APIRouter, Depends, HTTPException, Request, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.database import get_db
from app.models.user import User
from app.models.artwork import Artwork
from app.models.receipt import Receipt
from app.api.deps import get_current_user
from app.schemas.receipt_schema import ReceiptDetailResponse
from app.utils.send_email import send_purchase_email
import requests
import os
import base64
import hashlib
import hmac
import json
import uuid

router = APIRouter()

MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY")
MIDTRANS_CLIENT_KEY = os.getenv("MIDTRANS_CLIENT_KEY")
MIDTRANS_URL = "https://app.sandbox.midtrans.com/snap/v1/transactions"


class PurchaseRequest(BaseModel):
    artwork_id: str


@router.post("/initiate-payment")
async def initiate_payment(
    purchase_request: PurchaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    artwork = db.query(Artwork).filter(Artwork.id == purchase_request.artwork_id).first()
    if not artwork:
        raise HTTPException(status_code=404, detail="Karya seni tidak ditemukan")
    if artwork.price <= 0:
        raise HTTPException(status_code=400, detail="Karya ini gratis, tidak memerlukan pembayaran")

    existing_receipt = db.query(Receipt).filter_by(
        buyer_id=current_user.id,
        artwork_id=artwork.id
    ).first()
    if existing_receipt:
        raise HTTPException(status_code=400, detail="Karya ini sudah terjual.")

    order_id = f"ORDER-{uuid.uuid4()}"
    buyer_secret_code = uuid.uuid4().hex[:8]

    auth_header = base64.b64encode(f"{MIDTRANS_SERVER_KEY}:".encode()).decode()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_header}"
    }

    payload = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": int(artwork.price)
        },
        "customer_details": {
            "first_name": current_user.username,
            "email": current_user.email
        },
        "item_details": [
            {
                "id": str(artwork.id),
                "price": int(artwork.price),
                "quantity": 1,
                "name": artwork.title
            }
        ]
    }

    try:
        response = requests.post(MIDTRANS_URL, headers=headers, json=payload)
        if response.status_code != 201:
            raise HTTPException(status_code=502, detail="Gagal membuat transaksi di Midtrans")

        data = response.json()

        temp_receipt = Receipt(
            id=uuid.uuid4(),
            buyer_id=current_user.id,
            artwork_id=artwork.id,
            amount=artwork.price,
            buyer_secret_code=buyer_secret_code,
            order_id=order_id
        )
        db.add(temp_receipt)
        db.commit()

        return {
            "message": "Pembayaran berhasil diinisiasi",
            "snap_token": data.get("token"),
            "redirect_url": data.get("redirect_url"),
            "receipt_id": str(temp_receipt.id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payment-callback")
async def payment_callback(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    callback_data = json.loads(payload)

    order_id = callback_data.get("order_id")
    status_code = callback_data.get("status_code")
    gross_amount = callback_data.get("gross_amount")
    received_signature = callback_data.get("signature_key")

    server_key = os.getenv("MIDTRANS_SERVER_KEY")
    if not server_key:
        raise HTTPException(status_code=500, detail="Server key tidak ditemukan di environment")

    input_string = order_id + status_code + gross_amount + server_key
    expected_signature = hashlib.sha512(input_string.encode()).hexdigest()

    print("✅ COMPARING SIGNATURES:")
    print(f"Input: {order_id}+{status_code}+{gross_amount}+{server_key}")
    print(f"Expected: {expected_signature}")
    print(f"Received: {received_signature}")

    if received_signature != expected_signature:
        raise HTTPException(status_code=403, detail="Signature tidak valid")


    transaction_status = callback_data.get("transaction_status")
    if transaction_status == "settlement":
        item_details = callback_data.get("item_details", [])
        if item_details:
            artwork_id = item_details[0].get("id")
            buyer_email = callback_data.get("customer_details", {}).get("email")

            buyer = db.query(User).filter_by(email=buyer_email).first()
            if not buyer:
                raise HTTPException(status_code=404, detail="Pembeli tidak ditemukan")

            receipt = db.query(Receipt).filter_by(artwork_id=artwork_id, buyer_id=buyer.id).first()
            if not receipt:
                receipt = Receipt(
                    artwork_id=artwork_id,
                    buyer_id=buyer.id,
                    amount=gross_amount,
                    buyer_secret_code=uuid.uuid4().hex[:8]
                )
                db.add(receipt)

            receipt.order_id = order_id
            receipt.transaction_id = callback_data.get("transaction_id")
            receipt.payment_type = callback_data.get("payment_type")

            if status_code == "200":
                receipt.status = "paid"

            db.commit()
            db.refresh(receipt)

            await send_purchase_email(
                to_email=buyer.email,
                context={
        "artwork_title": receipt.artwork.title,
        "purchase_date": receipt.purchase_date.strftime("%d %B %Y"),
        "price": float(receipt.amount),
        "buyer_secret_code": receipt.buyer_secret_code,
        "download_url": f"http://localhost:8000{receipt.artwork.image_url}",
        "image_url": receipt.artwork.image_url,  
        "watermark_api": "http://localhost:8000/extract/extract-watermark"
    }
)


    return {"message": "Callback Midtrans diterima"}


@router.get("/my-purchases")
async def get_my_purchases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    receipts = db.query(Receipt).filter_by(buyer_id=current_user.id).all()
    return receipts

@router.get("/receipt/{id}", response_model=ReceiptDetailResponse)
async def get_receipt_detail(
    id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    receipt = db.query(Receipt).filter(Receipt.id == id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Struk tidak ditemukan")
    if receipt.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Kamu tidak memiliki akses ke struk ini")

    artwork = db.query(Artwork).filter_by(id=receipt.artwork_id).first()

    return {
        "receipt_id": str(receipt.id),
        "artwork_title": artwork.title,
        "image_url": artwork.image_url,
        "purchase_date": receipt.purchase_date,
        "price": float(receipt.amount),
        "buyer_secret_code": receipt.buyer_secret_code,
        "download_url": f"http://localhost:8000{artwork.image_url}",
        "watermark_api": "/extract/extract-watermark"
    }
