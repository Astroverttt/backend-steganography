# app/api/routes/verification.py

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.artwork import Artwork
from app.models.user import User
from app.steganography import extract_message_lsb
from app.utils.image_similarity import compute_all_hashes, is_similar_image
import os, uuid, hashlib, io
from PIL import Image

router = APIRouter()

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/verify_artwork", status_code=status.HTTP_200_OK)
async def verify_artwork(
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    temp_file_path = None
    
    try:
        content = await image.read()
        pil_image = Image.open(io.BytesIO(content)).convert("RGB")
        
        temp_file_name = f"temp_verify_{uuid.uuid4().hex}.png"
        temp_file_path = os.path.join(UPLOAD_DIR, temp_file_name)
        pil_image.save(temp_file_path)
            
        extracted_message = extract_message_lsb(temp_file_path)
        
        if not extracted_message:
            raise HTTPException(status_code=404, detail="Tidak ada watermark steganografi yang ditemukan.")
            
        parts = extracted_message.split("<USER_MESSAGE>")
        extracted_hash = parts[0].replace("COPYRIGHT:", "")
        
        # Cari semua karya seni dan bandingkan hash satu per satu
        artworks = db.query(Artwork).all()
        artwork = None
        for art in artworks:
            # Buat hash dari unique_key yang disimpan di database
            db_hash = hashlib.sha256(art.unique_key.encode()).hexdigest()
            if db_hash == extracted_hash:
                artwork = art
                break
        
        if not artwork:
            raise HTTPException(status_code=404, detail="Karya seni tidak ditemukan di database.")
            
        owner = db.query(User).filter(User.id == artwork.owner_id).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Pemilik karya seni tidak ditemukan.")
        
        # Verifikasi kesamaan gambar
        hashes_to_verify = compute_all_hashes(pil_image)
        if not is_similar_image(hashes_to_verify, pil_image, artwork):
            return {
                "verified": False,
                "message": "Watermark steganografi terdeteksi, tetapi gambar tidak cocok dengan gambar asli di database."
            }
        
        response = {
            "verified": True,
            "message": "Karya seni berhasil diverifikasi.",
            "title": artwork.title,
            "owner_name": owner.username,
            "description": artwork.description,
            "image_url": artwork.image_url,
            "unique_key": artwork.unique_key
        }
        
        return response
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verifikasi gagal: {str(e)}")
        
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)