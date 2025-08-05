from fastapi import APIRouter, Depends, HTTPException, Request, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.database import get_db
from app.models.user import User
from app.models.artwork import Artwork
from app.models.receipt import Receipt, ReceiptStatusEnum
from app.api.deps import get_current_user
from app.schemas.receipt_schema import ReceiptDetailResponse
from app.utils.send_email import send_purchase_email
import requests
import os
import base64
import hashlib
import json
import uuid
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY")
MIDTRANS_URL = "https://app.sandbox.midtrans.com/snap/v1/transactions"
BACKEND_API_BASE_URL = os.getenv("BACKEND_API_BASE_URL", "http://localhost:8000")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")


class PurchaseRequest(BaseModel):
    artwork_id: str
    success_redirect_url: str


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
        raise HTTPException(status_code=400, detail="Karya ini gratis, tidak memerlukan pembayaran.")

    existing_receipt = db.query(Receipt).filter(
        Receipt.buyer_id == current_user.id,
        Receipt.artwork_id == artwork.id,
        Receipt.status.in_([ReceiptStatusEnum.pending, ReceiptStatusEnum.paid])
    ).first()
    if existing_receipt:
        raise HTTPException(status_code=400, detail="Karya ini sudah dibeli atau sedang dalam proses pembayaran.")

    order_id = f"ORDER-{uuid.uuid4()}"
    buyer_secret_code_for_receipt = artwork.artwork_secret_code

    if not MIDTRANS_SERVER_KEY:
        raise HTTPException(status_code=500, detail="Kunci server Midtrans tidak diatur.")

    auth_header = base64.b64encode(f"{MIDTRANS_SERVER_KEY}:".encode()).decode()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_header}"
    }

    artwork_detail_url_base = purchase_request.success_redirect_url.split('?')[0]
    midtrans_notification_url = os.getenv("MIDTRANS_NOTIFICATION_URL_BASE")
    if not midtrans_notification_url:
        raise HTTPException(status_code=500, detail="URL notifikasi Midtrans tidak diatur.")
    midtrans_notification_full_url = f"{midtrans_notification_url}/api/payments/payment-callback"

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
        ],
        "callbacks": {
            "finish": purchase_request.success_redirect_url,
            "error": artwork_detail_url_base,
            "pending": artwork_detail_url_base,
            "notification": midtrans_notification_full_url
        }
    }

    try:
        response = requests.post(MIDTRANS_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        temp_receipt = Receipt(
            id=uuid.uuid4(),
            buyer_id=current_user.id,
            artwork_id=artwork.id,
            amount=artwork.price,
            buyer_secret_code=buyer_secret_code_for_receipt,
            order_id=order_id,
            status=ReceiptStatusEnum.pending
        )
        db.add(temp_receipt)
        db.commit()
        db.refresh(temp_receipt)

        return {
            "message": "Pembayaran berhasil diinisiasi",
            "snap_token": data.get("token"),
            "redirect_url": data.get("redirect_url"),
            "receipt_id": str(temp_receipt.id)
        }

    except requests.exceptions.RequestException:
        db.rollback()
        raise HTTPException(status_code=503, detail="Gagal terhubung ke layanan pembayaran.")
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Terjadi kesalahan internal: {e}")


@router.post("/payment-callback")
async def payment_callback(request: Request, db: Session = Depends(get_db)):
    payload_bytes = await request.body()
    try:
        callback_data = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    order_id = callback_data.get("order_id")
    status_code = callback_data.get("status_code")
    gross_amount = callback_data.get("gross_amount")
    received_signature = callback_data.get("signature_key")
    transaction_status = callback_data.get("transaction_status")

    server_key = os.getenv("MIDTRANS_SERVER_KEY")
    if not server_key:
        return {"message": "Server key not configured. Processing halted."}, 200

    input_string = f"{order_id}{status_code}{gross_amount}{server_key}"
    expected_signature = hashlib.sha512(input_string.encode()).hexdigest()

    if received_signature != expected_signature:
        raise HTTPException(status_code=403, detail="Signature tidak valid")

    receipt = db.query(Receipt).filter_by(order_id=order_id).first()
    if not receipt:
        return {"message": f"Receipt for order_id {order_id} not found. Processing halted."}, 200

    receipt.transaction_id = callback_data.get("transaction_id")
    receipt.payment_type = callback_data.get("payment_type")
    email_should_be_sent = False
    artwork_to_update = None

    if transaction_status == "settlement":
        if receipt.status != ReceiptStatusEnum.paid:
            receipt.status = ReceiptStatusEnum.paid
            email_should_be_sent = True
            artwork = db.query(Artwork).filter_by(id=receipt.artwork_id).first()
            if artwork and not artwork.is_sold:
                artwork.is_sold = True
                artwork_to_update = artwork
    elif transaction_status == "pending":
        if receipt.status not in [ReceiptStatusEnum.paid, ReceiptStatusEnum.pending]:
            receipt.status = ReceiptStatusEnum.pending
    elif transaction_status in ["expire", "cancel", "deny"]:
        if receipt.status != ReceiptStatusEnum.paid:
            receipt.status = (
                ReceiptStatusEnum.expired if transaction_status == "expire"
                else ReceiptStatusEnum.failed
            )

    try:
        db.commit()
        db.refresh(receipt)
        if artwork_to_update:
            db.refresh(artwork_to_update)

        if receipt.status == ReceiptStatusEnum.paid and email_should_be_sent:
            artwork = artwork_to_update or db.query(Artwork).filter_by(id=receipt.artwork_id).first()
            buyer = db.query(User).filter_by(id=receipt.buyer_id).first()
            if artwork and buyer:
                try:
                    await send_purchase_email(
                        to_email=buyer.email,
                        context={
                            "artwork_title": artwork.title,
                            "purchase_date": receipt.purchase_date.strftime("%d %B %Y"),
                            "price": float(receipt.amount),
                            "buyer_secret_code": receipt.buyer_secret_code,
                            "download_url": f"{FRONTEND_BASE_URL}{artwork.image_url}",
                            "watermark_api": f"{BACKEND_API_BASE_URL}/api/extract/extract-watermark",
                            "image_url": artwork.image_url,
                            "receipt_id": str(receipt.id)
                        }
                    )
                except Exception:
                    pass
    except Exception as e:
        db.rollback()
        return {"message": "Callback Midtrans diterima, tetapi ada masalah internal saat menyimpan data.", "error": str(e)}, 200

    return {"message": "Callback Midtrans diterima dan diproses"}, 200


@router.get("/my-purchases")
async def get_my_purchases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    receipts = db.query(Receipt).filter_by(buyer_id=current_user.id).all()
    return [
        {
            "receipt_id": str(r.id),
            "artwork_title": r.artwork.title if r.artwork else "Unknown Artwork",
            "image_url": r.artwork.image_url if r.artwork else None,
            "purchase_date": r.purchase_date,
            "price": float(r.amount),
            "buyer_secret_code": r.buyer_secret_code,
            "download_url": f"{FRONTEND_BASE_URL}{r.artwork.image_url}" if r.artwork and r.artwork.image_url else None,
            "watermark_api": f"{BACKEND_API_BASE_URL}/api/extract/extract-watermark",
            "status": r.status.value
        } for r in receipts
    ]


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
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork terkait tidak ditemukan.")

    return {
        "receipt_id": str(receipt.id),
        "artwork_title": artwork.title,
        "image_url": artwork.image_url,
        "purchase_date": receipt.purchase_date,
        "price": float(receipt.amount),
        "buyer_secret_code": receipt.buyer_secret_code,
        "download_url": f"{FRONTEND_BASE_URL}{artwork.image_url}",
        "watermark_api": f"{BACKEND_API_BASE_URL}/api/extract/extract-watermark",
        "status": receipt.status.value,
        "is_sold": artwork.is_sold
    }
