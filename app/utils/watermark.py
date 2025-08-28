# app/utils/watermark.py

from PIL import Image, ImageDraw, ImageFont
import os

def add_physical_watermark(image_obj, text, font_path="arial.ttf", font_size=30):
    watermarked_image = image_obj.copy().convert("RGBA")
    width, height = watermarked_image.size
    draw = ImageDraw.Draw(watermarked_image)

    try:
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
    except IOError:
        font = ImageFont.load_default()

    text_color = (255, 255, 255, 128)

    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    positions = [
        (10, 10),                                           # Pojok kiri atas
        (width - text_width - 10, 10),                      # Pojok kanan atas
        (10, height - text_height - 10),                    # Pojok kiri bawah
        (width - text_width - 10, height - text_height - 10) # Pojok kanan bawah
    ]

    for position in positions:
        draw.text(position, text, font=font, fill=text_color)
    
    return watermarked_image.convert("RGB")