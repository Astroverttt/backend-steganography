from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.steganography import extract_message_lsb, xor_encrypt_decrypt
import os, time


router = APIRouter()

class ExtractWatermarkRequest(BaseModel):
    image_url: str
    buyer_secret_code: str

@router.post("/extract-watermark")
def extract_watermark(data: ExtractWatermarkRequest):
    try:
        path = data.image_url.lstrip("/")
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Image not found")
        
        start = time.time()
        extracted = extract_message_lsb(path)
        elapsed = time.time() - start
        print(f"Extracted watermark in {elapsed:.4f} seconds")

        extracted = extract_message_lsb(path)

        if not extracted.startswith("COPYRIGHT:"):
            raise HTTPException(status_code=400, detail="Watermark not found")

        parts = extracted.split("<USER_MESSAGE>")
        copyright_hash = parts[0].replace("COPYRIGHT:", "")
        creator_message = None

        if len(parts) > 1:
            creator_message = xor_encrypt_decrypt(parts[1], data.buyer_secret_code)

        return {
            "extracted_in": f"{elapsed:.4f} seconds",
            "copyright_hash": copyright_hash,
            "creator_message": creator_message or "-"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
