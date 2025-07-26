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
import logging 

router = APIRouter()

logger = logging.getLogger(__name__)

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
    logger.info(f"PAYMENTS/INITIATE: Received purchase_request.artwork_id: '{purchase_request.artwork_id}'")

    artwork = db.query(Artwork).filter(Artwork.id == purchase_request.artwork_id).first()
    if not artwork:
        logger.error(f"PAYMENTS/INITIATE: Artwork with ID '{purchase_request.artwork_id}' not found.")
        raise HTTPException(status_code=404, detail="Karya seni tidak ditemukan")
    
    logger.info(f"PAYMENTS/INITIATE: Successfully retrieved artwork. Artwork ID from DB: '{artwork.id}', artwork_secret_code from DB: '{artwork.artwork_secret_code}'")


    if artwork.price <= 0:
        raise HTTPException(status_code=400, detail="Karya ini gratis, tidak memerlukan pembayaran")

    existing_receipt = db.query(Receipt).filter_by(
        buyer_id=current_user.id,
        artwork_id=artwork.id
    ).first()
    if existing_receipt:
        raise HTTPException(status_code=400, detail="Karya ini sudah terjual.")

    order_id = f"ORDER-{uuid.uuid4()}"
    
    buyer_secret_code_for_receipt = artwork.artwork_secret_code 
    logger.info(f"PAYMENTS/INITIATE: Assigning buyer_secret_code for receipt: '{buyer_secret_code_for_receipt}' (from artwork.artwork_secret_code)")

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
            logger.error(f"PAYMENTS/INITIATE: Midtrans API call failed with status {response.status_code}: {response.text}")
            raise HTTPException(status_code=502, detail="Gagal membuat transaksi di Midtrans")

        data = response.json()

        temp_receipt = Receipt(
            id=uuid.uuid4(),
            buyer_id=current_user.id,
            artwork_id=artwork.id,
            amount=artwork.price,
            buyer_secret_code=buyer_secret_code_for_receipt, 
            order_id=order_id
        )
        logger.info(f"PAYMENTS/INITIATE: Attempting to save temp_receipt with ID: '{temp_receipt.id}', buyer_secret_code: '{temp_receipt.buyer_secret_code}'")
        db.add(temp_receipt)
        db.commit()
        db.refresh(temp_receipt)
        logger.info(f"PAYMENTS/INITIATE: Temp_receipt successfully saved. Confirmed buyer_secret_code from DB: '{temp_receipt.buyer_secret_code}'")


        return {
            "message": "Pembayaran berhasil diinisiasi",
            "snap_token": data.get("token"),
            "redirect_url": data.get("redirect_url"),
            "receipt_id": str(temp_receipt.id)
        }

    except Exception as e:
        logger.error(f"PAYMENTS/INITIATE: Unexpected error during payment initiation: {e}", exc_info=True)
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

    logger.info("✅ COMPARING SIGNATURES:")
    logger.info(f"Input: {order_id}+{status_code}+{gross_amount}+{server_key}")
    logger.info(f"Expected: {expected_signature}")
    logger.info(f"Received: {received_signature}")

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

            receipt = db.query(Receipt).filter_by(order_id=order_id).first()

            if not receipt:
                logger.error(f"PAYMENTS/CALLBACK: Receipt for order_id {order_id} not found after settlement. This indicates an issue in the payment initiation flow.")
                raise HTTPException(status_code=404, detail=f"Receipt for order_id {order_id} not found. This indicates an issue in the payment initiation flow.")
            
            receipt.transaction_id = callback_data.get("transaction_id")
            receipt.payment_type = callback_data.get("payment_type")
            
            if status_code == "200":
                receipt.status = "paid"

            db.commit()
            db.refresh(receipt)
            logger.info(f"PAYMENTS/CALLBACK: Retrieved receipt {receipt.id} with buyer_secret_code: {receipt.buyer_secret_code}")


            await send_purchase_email(
                to_email=buyer.email,
                context={
                    "artwork_title": receipt.artwork.title,
                    "purchase_date": receipt.purchase_date.strftime("%d %B %Y"),
                    "price": float(receipt.amount),
                    "buyer_secret_code": receipt.buyer_secret_code, 
                    "download_url": f"http://localhost:8000{receipt.artwork.image_url}",
                    "image_url": receipt.artwork.image_url,
                    "watermark_api": "http://localhost:8000/api/extract/extract-watermark",
                    "receipt_id": str(receipt.id)
                }
            )
            logger.info(f"PAYMENTS/CALLBACK: Email sent with buyer_secret_code: {receipt.buyer_secret_code}")


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
        "watermark_api": "/api/extract/extract-watermark"
    }