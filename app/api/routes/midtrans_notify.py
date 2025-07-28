from fastapi import APIRouter, Request, HTTPException, Depends
import hmac, hashlib, os
import json
import logging
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.database import get_db 
from app.models.artwork import Artwork 

router = APIRouter()
logger = logging.getLogger(__name__) 

MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY")

@router.post("/midtrans/notification")
async def handle_midtrans_notification(request: Request, db: Session = Depends(get_db)): 
    try:
        body = await request.body()
        data = json.loads(body)
        logger.info(f"Midtrans Notification Received: {json.dumps(data, indent=2)}") 

        order_id = data.get("order_id")
        status_code = data.get("status_code")
        gross_amount = data.get("gross_amount")
        signature_key = data.get("signature_key")
        transaction_status = data.get("transaction_status")

        if not all([order_id, status_code, gross_amount, signature_key, transaction_status]):
            logger.warning(f"Missing required data in Midtrans notification: {data}")
            raise HTTPException(status_code=400, detail="Data notifikasi tidak lengkap")

        expected_signature = hashlib.sha512(
            f"{order_id}{status_code}{gross_amount}{MIDTRANS_SERVER_KEY}".encode()
        ).hexdigest()

        if signature_key != expected_signature:
            logger.warning(f"Invalid signature key for order_id: {order_id}. Received: {signature_key}, Expected: {expected_signature}")
            raise HTTPException(status_code=401, detail="Signature tidak valid")

        try:
            artwork_id = UUID(order_id)
        except ValueError:
            logger.error(f"Invalid artwork ID format in order_id: {order_id}")
            raise HTTPException(status_code=400, detail="ID karya seni tidak valid dari notifikasi")

        artwork = db.query(Artwork).filter(Artwork.id == artwork_id).first()

        if not artwork:
            logger.error(f"Artwork with ID {artwork_id} not found for notification processing.")
            raise HTTPException(status_code=404, detail="Karya seni tidak ditemukan untuk notifikasi ini")

        if transaction_status == 'capture' or transaction_status == 'settlement':
            if not artwork.is_sold:
                artwork.is_sold = True
                db.add(artwork)
                db.commit()
                db.refresh(artwork)
                logger.info(f"Artwork {artwork_id} successfully marked as SOLD (status: {transaction_status}).")
                return {"message": "Notifikasi pembayaran berhasil diproses: Karya seni terjual."}
            else:
                logger.info(f"Artwork {artwork_id} was already sold (status: {transaction_status}). No update needed.")
                return {"message": "Notifikasi pembayaran diterima: Karya seni sudah terjual."}
        elif transaction_status == 'pending':
            logger.info(f"Payment for artwork {artwork_id} is pending.")
            return {"message": "Notifikasi pembayaran diterima: Pembayaran tertunda."}
        elif transaction_status == 'deny' or transaction_status == 'expire' or transaction_status == 'cancel':
            logger.warning(f"Payment for artwork {artwork_id} failed or was cancelled (status: {transaction_status}).")

            return {"message": f"Notifikasi pembayaran diterima: Pembayaran {transaction_status}."}
        else:
            logger.warning(f"Unhandled transaction status for artwork {artwork_id}: {transaction_status}.")
            return {"message": "Notifikasi diterima dengan status yang tidak ditangani."}

    except json.JSONDecodeError:
        logger.error("Invalid JSON format in Midtrans notification body.")
        raise HTTPException(status_code=400, detail="Format JSON tidak valid")
    except HTTPException as e:
        raise e 
    except Exception as e:
        logger.error(f"Failed to process Midtrans notification due to internal error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gagal memproses notifikasi: {str(e)}")