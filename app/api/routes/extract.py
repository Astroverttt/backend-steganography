import logging # Tambahkan ini
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.steganography import extract_message_lsb, xor_encrypt_decrypt
import os
import time
import requests
from tempfile import NamedTemporaryFile

router = APIRouter()

logger = logging.getLogger(__name__)

class ExtractWatermarkRequest(BaseModel):
    image_url: str
    buyer_secret_code: str

@router.post("/extract-watermark")
def extract_watermark(data: ExtractWatermarkRequest):
    temp_path = None 
    is_url = False
    try:
        image_path = data.image_url.strip()
        is_url = image_path.startswith("http://") or image_path.startswith("https://")
        
        logger.info(f"EXTRACT: Received request for image_url: {image_path}")
        logger.info(f"EXTRACT: Received buyer_secret_code for decryption: '{data.buyer_secret_code}'") 

        if is_url:
            response = requests.get(image_path)
            if response.status_code != 200:
                logger.error(f"EXTRACT: Failed to download image from URL: {image_path}, Status: {response.status_code}")
                raise HTTPException(status_code=404, detail="Unable to download image from URL")
            
            with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(response.content)
                temp_path = tmp.name
            logger.info(f"EXTRACT: Image downloaded to temporary path: {temp_path}")
        else:
            temp_path = image_path.lstrip("/")
            if not os.path.exists(temp_path):
                logger.error(f"EXTRACT: Image not found on server at path: {temp_path}")
                raise HTTPException(status_code=404, detail="Image not found on server")
            logger.info(f"EXTRACT: Using local image path: {temp_path}")

        start = time.time()
        extracted = extract_message_lsb(temp_path)
        elapsed = time.time() - start
        logger.info(f"EXTRACT: Raw extracted message: '{extracted}' (took {elapsed:.4f}s)") 

        if not extracted.startswith("COPYRIGHT:"):
            logger.warning(f"EXTRACT: Watermark not found or invalid format. Extracted: '{extracted[:50]}...'")
            raise HTTPException(status_code=400, detail="Watermark not found")

        parts = extracted.split("<USER_MESSAGE>")
        copyright_hash = parts[0].replace("COPYRIGHT:", "").strip()
        creator_message = None

        if len(parts) > 1:
            encrypted_creator_message = parts[1]
            logger.info(f"EXTRACT: Encrypted creator message part: '{encrypted_creator_message}'")
            logger.info(f"EXTRACT: Attempting to decrypt with buyer_secret_code: '{data.buyer_secret_code}'")
            creator_message = xor_encrypt_decrypt(encrypted_creator_message, data.buyer_secret_code)
            logger.info(f"EXTRACT: Decrypted creator message: '{creator_message}'") 
        return {
            "extracted_in": f"{elapsed:.4f} seconds",
            "copyright_hash": copyright_hash,
            "creator_message": creator_message or "-"
        }

    except HTTPException as e:
        logger.error(f"EXTRACT: HTTP Exception: {e.detail} (Status: {e.status_code})")
        raise e
    except Exception as e:
        logger.error(f"EXTRACT: Unexpected error during extraction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    finally:
        if is_url and temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"EXTRACT: Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.error(f"EXTRACT: Failed to remove temporary file {temp_path}: {e}")