import os
from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, status # <-- Tambahkan 'status'
from PIL import Image
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.models.artwork import Artwork
from app.api.deps import get_current_user
from app.steganography import embed_message_lsb, xor_encrypt_decrypt, extract_message_lsb
import uuid
import hashlib
import imagehash
import io

router = APIRouter()

UPLOAD_DIR = "static/uploads"
WATERMARKED_DIR = "static/watermarked"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(WATERMARKED_DIR, exist_ok=True)

@router.post("/upload", status_code=status.HTTP_201_CREATED) # <-- Perbaikan di sini
async def upload_artwork(
    title: str = Form(...),
    description: str = Form(None),
    category: str = Form(None),
    license_type: str = Form("FREE"),
    price: float = Form(0.00),
    image: UploadFile = File(...),
    watermark_creator_message: str = Form(None), # Pesan dari user
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    temp_file_path = None # Inisialisasi untuk memastikan bisa diakses di blok except
    watermarked_image_path = None

    try:
        unique_key = f"UniqueKey_{title.replace(' ', '')}_{current_user.username}_{uuid.uuid4().hex[:6]}"
        file_extension = image.filename.split(".")[-1]
        
        # Simpan gambar asli sementara untuk pemrosesan dan pHash
        temp_file_name = f"{uuid.uuid4().hex}.{file_extension}"
        temp_file_path = os.path.join(UPLOAD_DIR, temp_file_name)
        
        content = await image.read()

        # Hitung Perceptual Hash (pHash)
        pil_image = Image.open(io.BytesIO(content))
        perceptual_hash = str(imagehash.average_hash(pil_image))
        
        # Simpan file asli ke disk untuk proses steganografi
        with open(temp_file_path, "wb") as f:
            f.write(content)
        
        # --- LOGIKA STEGANOGRAFI BARU ---
        # 1. Gabungkan watermark hak cipta dan pesan creator
        watermark_hak_cipta = hashlib.sha256(unique_key.encode()).hexdigest()
        
        # Jika ada pesan creator, enkripsi dengan kunci rahasia buyer
        buyer_secret_code = uuid.uuid4().hex[:16] # Kunci ini perlu disimpan atau dikembalikan ke buyer
        pesan_gabungan = f"COPYRIGHT:{watermark_hak_cipta}"
        
        if watermark_creator_message:
            # Enkripsi pesan creator dengan buyer_secret_code
            encrypted_creator_message = xor_encrypt_decrypt(watermark_creator_message, buyer_secret_code)
            # Gabungkan dengan penanda yang jelas untuk pemisahan saat ekstraksi
            pesan_gabungan += f"<USER_MESSAGE>{encrypted_creator_message}"
        
        # Sekarang panggil embed_message_lsb dengan hanya DUA argumen
        watermarked_image_path = embed_message_lsb(temp_file_path, pesan_gabungan)

        # Hapus gambar asli yang bersifat sementara setelah steganografi selesai
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        # Pindahkan gambar yang sudah di-watermark ke direktori WATERMARKED_DIR
        final_image_name = f"{unique_key}_stego.{file_extension}"
        final_image_path = os.path.join(WATERMARKED_DIR, final_image_name)
        os.rename(watermarked_image_path, final_image_path) # watermarked_image_path adalah output dari embed_message_lsb

        image_url_db = f"/static/watermarked/{final_image_name}"

        # Buat entri Artwork di database
        artwork = Artwork(
            id=uuid.uuid4(),
            user_id=current_user.id,
            title=title,
            description=description,
            category=category,
            license_type=license_type,
            price=price,
            image_url=image_url_db,
            unique_key=unique_key,
            hash=perceptual_hash,
        
        )
        db.add(artwork)
        db.commit()
        db.refresh(artwork)

        return {
            "message": "Artwork uploaded successfully with steganography",
            "artwork_id": artwork.id,
            "image_url": image_url_db,
            "buyer_secret_code": buyer_secret_code # Penting: kembalikan ini ke pembeli!
        }

    except ValueError as ve:
        # Pastikan file sementara dihapus jika ada error
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        # Hapus juga gambar watermarked jika sudah terbuat sebelum error fatal
        if watermarked_image_path and os.path.exists(watermarked_image_path):
            os.remove(watermarked_image_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # Pastikan file sementara dihapus jika ada error
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        # Hapus juga gambar watermarked jika sudah terbuat sebelum error fatal
        if watermarked_image_path and os.path.exists(watermarked_image_path):
            os.remove(watermarked_image_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Terjadi error saat mengunggah: {str(e)}")
