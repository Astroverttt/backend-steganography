from fastapi import APIRouter, Request, HTTPException
import hmac, hashlib, os
import json

router = APIRouter()

MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY")

@router.post("/midtrans/notification")
async def handle_midtrans_notification(request: Request):
    try:
        body = await request.body()
        data = json.loads(body)

        # Verifikasi signature
        order_id = data["order_id"]
        status_code = data["status_code"]
        gross_amount = data["gross_amount"]
        signature_key = data["signature_key"]

        expected_signature = hashlib.sha512(
            f"{order_id}{status_code}{gross_amount}{MIDTRANS_SERVER_KEY}".encode()
        ).hexdigest()

        if signature_key != expected_signature:
            raise HTTPException(status_code=400, detail="Signature tidak valid")

        transaction_status = data.get("transaction_status")

        return {"message": f"Notifikasi diterima, status: {transaction_status}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses notifikasi: {str(e)}")
