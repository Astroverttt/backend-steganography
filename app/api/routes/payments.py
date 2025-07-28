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
    success_redirect_url: str


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

    artwork_detail_url_base = purchase_request.success_redirect_url.split('?')[0]

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
            "pending": artwork_detail_url_base          
        }
        
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
    logger.info(f"PAYMENTS/CALLBACK: Received raw callback data: {json.dumps(callback_data, indent=2)}")

    order_id = callback_data.get("order_id")
    status_code = callback_data.get("status_code")
    gross_amount = callback_data.get("gross_amount")
    received_signature = callback_data.get("signature_key")
    transaction_status = callback_data.get("transaction_status") 

    logger.info(f"PAYMENTS/CALLBACK: Extracted data - Order ID: {order_id}, Status Code: {status_code}, Gross Amount: {gross_amount}, Transaction Status: {transaction_status}")


    server_key = os.getenv("MIDTRANS_SERVER_KEY")
    if not server_key:
        logger.error("PAYMENTS/CALLBACK: Server key not found in environment variables.")
        raise HTTPException(status_code=500, detail="Server key tidak ditemukan di environment")

    input_string = f"{order_id}{status_code}{gross_amount}{server_key}" 
    expected_signature = hashlib.sha512(input_string.encode()).hexdigest()

    logger.info("PAYMENTS/CALLBACK: COMPARING SIGNATURES:")
    logger.info(f"PAYMENTS/CALLBACK: Input for signature: {input_string}")
    logger.info(f"PAYMENTS/CALLBACK: Expected Signature: {expected_signature}")
    logger.info(f"PAYMENTS/CALLBACK: Received Signature: {received_signature}")

    if received_signature != expected_signature:
        logger.warning(f"PAYMENTS/CALLBACK: Signature mismatch for Order ID: {order_id}. Received: {received_signature}, Expected: {expected_signature}")
        raise HTTPException(status_code=403, detail="Signature tidak valid")
    
    logger.info(f"PAYMENTS/CALLBACK: Signature successfully verified for Order ID: {order_id}.")

    # --- Start of critical changes ---
    # Always try to fetch the receipt first using order_id
    receipt = db.query(Receipt).filter_by(order_id=order_id).first()
    if not receipt:
        logger.error(f"PAYMENTS/CALLBACK: Receipt for order_id {order_id} not found in database. This indicates a prior issue or an invalid callback.")
        raise HTTPException(status_code=404, detail=f"Receipt for order_id {order_id} not found.")

    logger.info(f"PAYMENTS/CALLBACK: Found existing receipt {receipt.id} for Order ID: {order_id}. Current status: {receipt.status}.")

    # Update receipt details from callback regardless of status, then handle specific statuses
    receipt.transaction_id = callback_data.get("transaction_id")
    receipt.payment_type = callback_data.get("payment_type")
    
    # Update status based on Midtrans transaction_status
    if transaction_status == "settlement":
        receipt.status = "paid"
        logger.info(f"PAYMENTS/CALLBACK: Transaction status is 'settlement' for Order ID: {order_id}. Updating receipt status to 'paid'.")
    elif transaction_status == "pending":
        receipt.status = "pending"
        logger.info(f"PAYMENTS/CALLBACK: Transaction status is 'pending' for Order ID: {order_id}. Updating receipt status to 'pending'.")
    elif transaction_status in ["expire", "cancel", "deny"]:
        receipt.status = "failed" # Or "cancelled" based on your enum
        logger.warning(f"PAYMENTS/CALLBACK: Transaction status is '{transaction_status}' for Order ID: {order_id}. Updating receipt status to '{receipt.status}'.")
    else:
        logger.info(f"PAYMENTS/CALLBACK: Unhandled transaction status: {transaction_status} for Order ID: {order_id}. Receipt status remains '{receipt.status}'.")

    db.add(receipt) # Add updated receipt to session
    db.commit()
    db.refresh(receipt)
    logger.info(f"PAYMENTS/CALLBACK: Receipt {receipt.id} (Order ID: {order_id}) successfully updated in DB. New status: {receipt.status}.")


    if transaction_status == "settlement":
        # Now that we have the receipt, we can get artwork_id and buyer_id from it
        artwork = db.query(Artwork).filter_by(id=receipt.artwork_id).first()
        buyer = db.query(User).filter_by(id=receipt.buyer_id).first()

        if not artwork:
            logger.error(f"PAYMENTS/CALLBACK: Artwork {receipt.artwork_id} not found for receipt {receipt.id} (Order ID: {order_id}). Cannot update artwork or send email.")
            # Do not raise HTTPException, as the payment is settled. Just log.
        elif not buyer:
            logger.error(f"PAYMENTS/CALLBACK: Buyer {receipt.buyer_id} not found for receipt {receipt.id} (Order ID: {order_id}). Cannot send email.")
            # Do not raise HTTPException, as the payment is settled. Just log.
        else:
            logger.info(f"PAYMENTS/CALLBACK: Found Artwork '{artwork.title}' and Buyer '{buyer.email}' for Order ID: {order_id}.")
            
            # Update artwork status if not already sold
            if not artwork.is_sold:
                artwork.is_sold = True
                db.add(artwork)
                db.commit()
                db.refresh(artwork)
                logger.info(f"PAYMENTS/CALLBACK: Artwork {artwork.id} marked as sold for Order ID: {order_id}.")
            else:
                logger.info(f"PAYMENTS/CALLBACK: Artwork {artwork.id} was already marked as sold for Order ID: {order_id}. No update needed.")

            # Attempt to send email
            try:
                await send_purchase_email(
                    to_email=buyer.email,
                    context={
                        "artwork_title": artwork.title,
                        "purchase_date": receipt.purchase_date.strftime("%d %B %Y"),
                        "price": float(receipt.amount),
                        "buyer_secret_code": receipt.buyer_secret_code, 
                        "download_url": f"http://localhost:8000{artwork.image_url}",
                        "image_url": artwork.image_url,
                        "watermark_api": "http://localhost:8000/api/extract/extract-watermark",
                        "receipt_id": str(receipt.id)
                    }
                )
                logger.info(f"PAYMENTS/CALLBACK: Purchase email successfully sent to {buyer.email} for Order ID: {order_id}.")
            except Exception as e:
                logger.error(f"PAYMENTS/CALLBACK: ERROR sending purchase email for Order ID {order_id} to {buyer.email}: {e}", exc_info=True)
                # Keep 200 OK response to Midtrans even if email fails, as the payment is settled.

    # --- End of critical changes ---

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