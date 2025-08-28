from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.models.artwork import Artwork, generate_unique_key
from app.api.deps import get_current_user
from app.steganography import embed_message_lsb, xor_encrypt_decrypt
from app.utils.image_similarity import compute_all_hashes, is_similar_image
from app.utils.send_email import send_certificate_email
import os, uuid, hashlib, io
from PIL import Image, ImageDraw, ImageFont

router = APIRouter()

UPLOAD_DIR = "static/uploads"
WATERMARKED_DIR = "static/watermarked"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(WATERMARKED_DIR, exist_ok=True)

# app/utils/watermark.py atau di dalam uploads.py

def add_physical_watermark(image_obj, text, font_path="arial.ttf", font_size=None):
    watermarked_image = image_obj.copy().convert("RGBA")
    width, height = watermarked_image.size
    draw = ImageDraw.Draw(watermarked_image)
    
    # Auto-calculate font size based on image dimensions if not provided
    if font_size is None:
        font_size = max(24, min(width, height) // 25)  # Responsive font size
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()
    
    # Semi-transparent white text with better opacity
    text_color = (255, 255, 255, 180)
    
    # Stronger dark outline for better contrast
    outline_color = (0, 0, 0, 200)
    outline_width = 2
    
    # Calculate text dimensions
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Better positioned watermarks with more padding
    padding = max(20, min(width, height) // 30)
    
    positions = [
        # Top corners
        (padding, padding),
        (width - text_width - padding, padding),
        # Bottom corners  
        (padding, height - text_height - padding),
        (width - text_width - padding, height - text_height - padding),
        # Center positions for better coverage
        (width//2 - text_width//2, padding),  # Top center
        (width//2 - text_width//2, height - text_height - padding),  # Bottom center
    ]
    
    # Create better outline effect
    outline_offsets = [
        (-outline_width, -outline_width), (0, -outline_width), (outline_width, -outline_width),
        (-outline_width, 0), (outline_width, 0),
        (-outline_width, outline_width), (0, outline_width), (outline_width, outline_width)
    ]
    
    for position in positions:
        # Draw multi-directional outline for better visibility
        for offset_x, offset_y in outline_offsets:
            draw.text(
                (position[0] + offset_x, position[1] + offset_y), 
                text, font=font, fill=outline_color
            )
        
        # Draw main text
        draw.text(position, text, font=font, fill=text_color)
    
    # Optional: Add a subtle diagonal watermark in the center
    # Rotate text for diagonal effect
    center_x, center_y = width // 2, height // 2
    
    # Create a temporary image for rotated text
    temp_img = Image.new('RGBA', (text_width + 40, text_height + 40), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    
    # Draw outline on temp image
    for offset_x, offset_y in outline_offsets:
        temp_draw.text(
            (20 + offset_x, 20 + offset_y), 
            text, font=font, fill=(0, 0, 0, 100)
        )
    
    # Draw main text on temp image with lower opacity for center watermark
    temp_draw.text((20, 20), text, font=font, fill=(255, 255, 255, 80))
    
    # Rotate the temporary image
    rotated_temp = temp_img.rotate(45, expand=1)
    
    # Paste rotated watermark in center
    paste_x = center_x - rotated_temp.width // 2
    paste_y = center_y - rotated_temp.height // 2
    watermarked_image.paste(rotated_temp, (paste_x, paste_y), rotated_temp)
    
    return watermarked_image.convert("RGB")

@router.post("/uploads", status_code=status.HTTP_201_CREATED)
async def upload_artwork(
    title: str = Form(...),
    description: str = Form(None),
    category: str = Form(None),
    license_type: str = Form("FREE"),
    price: float = Form(0.00),
    image: UploadFile = File(...),
    watermark_creator_message: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    temp_file_path = None
    watermarked_image_path = None
    physically_watermarked_temp_path = None

    try:
        merged_user = db.merge(current_user)
        user_id_str = str(merged_user.id)
        unique_key = generate_unique_key(user_id_str, title, image.filename)
        _, file_extension = os.path.splitext(image.filename)
        file_extension = file_extension.lstrip(".").lower()
        
        license_type = license_type.upper()
        if license_type not in ["FREE", "PAID"]:
            raise HTTPException(status_code=400, detail="Tipe lisensi tidak valid.")
        
        if license_type == "FREE":
            price = 0.0
        elif license_type == "PAID":
            if price <= 0.0:
                raise HTTPException(status_code=400, detail="Harga harus diisi jika lisensi berbayar.")

        content = await image.read()
        pil_image = Image.open(io.BytesIO(content)).convert("RGB")
        uploaded_hashes = compute_all_hashes(pil_image)

        existing_artworks = db.query(Artwork).all()
        for artwork_item in existing_artworks: 
            if is_similar_image(uploaded_hashes, pil_image, artwork_item):
                raise HTTPException(status_code=400, detail="Gambar Ditemukan mirip atau sudah pernah diunggap (terdeteksi duplikat).")

        watermark_text = f"by {merged_user.username}"
        pil_image_with_watermark = add_physical_watermark(pil_image, watermark_text)
        
        physically_watermarked_temp_path = os.path.join(UPLOAD_DIR, f"physical_wm_{uuid.uuid4().hex}.{file_extension}")
        pil_image_with_watermark.save(physically_watermarked_temp_path)

        watermark_hak_cipta = hashlib.sha256(unique_key.encode()).hexdigest()
        artwork_secret_code_for_watermark = None
        pesan_gabungan = f"COPYRIGHT:{watermark_hak_cipta}"

        if watermark_creator_message:
            artwork_secret_code_for_watermark = uuid.uuid4().hex[:8] 
            encrypted = xor_encrypt_decrypt(watermark_creator_message, artwork_secret_code_for_watermark)
            pesan_gabungan += f"<USER_MESSAGE>{encrypted}"

        watermarked_image_path = embed_message_lsb(physically_watermarked_temp_path, pesan_gabungan)

        if os.path.exists(physically_watermarked_temp_path):
            os.remove(physically_watermarked_temp_path)

        filename_without_ext, _ = os.path.splitext(unique_key)
        final_image_name = f"{filename_without_ext}.{file_extension}"
        final_image_path = os.path.join(WATERMARKED_DIR, final_image_name)
        os.rename(watermarked_image_path, final_image_path)

        BASE_URL = "http://localhost:8000"
        image_url_db = f"/static/watermarked/{final_image_name}"
        image_url_full = f"{BASE_URL}{image_url_db}"

        artwork = Artwork(
            id=uuid.uuid4(),
            owner_id=merged_user.id,
            title=title,
            description=description,
            category=category,
            license_type=license_type,
            price=price,
            image_url=image_url_db,
            unique_key=unique_key,
            hash=uploaded_hashes["ahash"],
            hash_phash=uploaded_hashes["phash"],
            hash_dhash=uploaded_hashes["dhash"],
            hash_whash=uploaded_hashes["whash"],
            artwork_secret_code=artwork_secret_code_for_watermark
        )
        db.add(artwork)
        db.commit()
        db.refresh(artwork)

        await send_certificate_email(
            to_email=merged_user.email,
            context={
                "title": title,
                "category": category or "-",
                "description": description or "-",
                "unique_key": unique_key,
                "buyer_code": artwork_secret_code_for_watermark if artwork_secret_code_for_watermark else "N/A",
                "image_url": image_url_full
            }
        )

        return {
            "message": "Artwork uploaded successfully with steganography",
            "artwork_id": artwork.id,
            "image_url": image_url_db,
            "unique_key": unique_key,
            "copyright_hash": watermark_hak_cipta,
            "buyer_secret_code": artwork_secret_code_for_watermark
        }
    except HTTPException as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if watermarked_image_path and os.path.exists(watermarked_image_path):
            os.remove(watermarked_image_path)
        if physically_watermarked_temp_path and os.path.exists(physically_watermarked_temp_path):
            os.remove(physically_watermarked_temp_path)
        raise e
    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if watermarked_image_path and os.path.exists(watermarked_image_path):
            os.remove(watermarked_image_path)
        if physically_watermarked_temp_path and os.path.exists(physically_watermarked_temp_path):
            os.remove(physically_watermarked_temp_path)
        raise HTTPException(status_code=500, detail=f"Upload gagal: {str(e)}")