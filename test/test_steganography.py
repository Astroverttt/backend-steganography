# backend/test/test_steganography.py
import os
import sys
import unittest
import string
from PIL import Image
from PIL.ImageEnhance import Brightness

# pastikan bisa import package app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.steganography import (
    embed_message_lsb_from_pil_image,
    extract_message_lsb_from_pil_image,
    extract_message_lsb,  # tambahin ini
    rotate_image,
)

# ======================
# KONFIG
# ======================
WATERMARKED_IMAGE_PATH = 'static/watermarked/70d1a9cb_0b737b7c-14a5-4403-b311-218cb9a34c43_Drake.png'
ORIGINAL_MESSAGE = "COPYRIGHT:c87f3...c79e<USER_MESSAGE>..."
OUTPUT_DIR = "test_results"

# global untuk laporan
SUCCESSFUL_TESTS = []


# ======================
# UTIL LOGGING & VALIDASI
# ======================
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def summarize_text(s: str, max_len: int = 80) -> str:
    if s is None:
        return "None"
    s = s.replace("\n", " ")
    return s if len(s) <= max_len else s[:max_len] + "…"

def looks_like_valid_extract(extracted: str) -> bool:
    if not extracted:
        return False
    if ORIGINAL_MESSAGE and ORIGINAL_MESSAGE in extracted:
        return True
    # prefix check
    common = 0
    for a, b in zip(extracted, ORIGINAL_MESSAGE):
        if a == b:
            common += 1
        else:
            break
    if common >= 8:
        return True
    # printable ratio check
    printable = set(string.printable)
    printable_ratio = sum(c in printable for c in extracted) / max(1, len(extracted))
    if printable_ratio >= 0.85 and len(extracted) >= 8:
        return True
    return False

def log_check(title: str, extracted: str):
    ok = looks_like_valid_extract(extracted)
    status = "Utuh ✅" if ok else "Rusak ❌"
    print(f"[TEST] {title}: {status} | len={len(extracted or '')} | sample='{summarize_text(extracted)}'")
    if ok:
        SUCCESSFUL_TESTS.append(title)


# ======================
# UNIT TEST
# ======================
class TestSteganography(unittest.TestCase):

    def setUp(self):
        self.image = Image.new("RGB", (100, 100), "white")
        self.message = "Hello World"

    def test_embed_and_extract(self):
        encoded = embed_message_lsb_from_pil_image(self.image, self.message)
        extracted = extract_message_lsb_from_pil_image(encoded)
        self.assertEqual(extracted, self.message)

    def test_rotate(self):
        r90 = rotate_image(self.image, 90)
        self.assertEqual(r90.size, (100, 100))
        r180 = rotate_image(self.image, 180)
        self.assertEqual(r180.size, (100, 100))


# ======================
# ROBUSTNESS TEST
# ======================
def test_robustness():
    ensure_dir(OUTPUT_DIR)

    if not os.path.exists(WATERMARKED_IMAGE_PATH):
        print(f"❌ Error: File tidak ditemukan di {WATERMARKED_IMAGE_PATH}")
        return

    original_image = Image.open(WATERMARKED_IMAGE_PATH).convert("RGB")
    width, height = original_image.size

    print("=" * 70)
    print("🔍 MULAI PENGUJIAN ROBUSTNESS LSB")
    print(f"   File : {WATERMARKED_IMAGE_PATH}")
    print(f"   Size : {width} x {height}")
    print("=" * 70)

    # 0. Ekstraksi normal (gambar utuh, belum dimodifikasi) → pakai fungsi yg sama dengan API
    try:
        extracted = extract_message_lsb(WATERMARKED_IMAGE_PATH)
    except Exception as e:
        extracted = f"[ERROR] {e}"
    log_check("Full Image (original utuh)", extracted)

    # 1. Crop
    cropped = original_image.crop((50, 50, width - 50, height - 50))
    cropped.save(os.path.join(OUTPUT_DIR, "cropped.png"))
    try:
        extracted = extract_message_lsb_from_pil_image(cropped)
    except Exception as e:
        extracted = f"[ERROR] {e}"
    log_check("Crop (border=50px)", extracted)

    # 2. Scaling
    scaled = original_image.resize((max(1, width // 2), max(1, height // 2)))
    scaled.save(os.path.join(OUTPUT_DIR, "scaled_50.png"))
    try:
        extracted = extract_message_lsb_from_pil_image(scaled)
    except Exception as e:
        extracted = f"[ERROR] {e}"
    log_check("Scaling (50%)", extracted)

    # 3. Brightness
    brighter = Brightness(original_image).enhance(1.5)
    brighter.save(os.path.join(OUTPUT_DIR, "brighter_150.png"))
    try:
        extracted = extract_message_lsb_from_pil_image(brighter)
    except Exception as e:
        extracted = f"[ERROR] {e}"
    log_check("Brightness (+50%)", extracted)

    # 4a. Stretch horizontal
    stretched_h = original_image.resize((int(width * 1.5), height))
    stretched_h.save(os.path.join(OUTPUT_DIR, "stretch_h_150.png"))
    try:
        extracted = extract_message_lsb_from_pil_image(stretched_h)
    except Exception as e:
        extracted = f"[ERROR] {e}"
    log_check("Stretch Horizontal (150%)", extracted)

    # 4b. Compress horizontal
    compressed_h = original_image.resize((max(1, int(width * 0.5)), height))
    compressed_h.save(os.path.join(OUTPUT_DIR, "compress_h_50.png"))
    try:
        extracted = extract_message_lsb_from_pil_image(compressed_h)
    except Exception as e:
        extracted = f"[ERROR] {e}"
    log_check("Compress Horizontal (50%)", extracted)

    # 4c. Stretch vertical
    stretched_v = original_image.resize((width, int(height * 1.5)))
    stretched_v.save(os.path.join(OUTPUT_DIR, "stretch_v_150.png"))
    try:
        extracted = extract_message_lsb_from_pil_image(stretched_v)
    except Exception as e:
        extracted = f"[ERROR] {e}"
    log_check("Stretch Vertical (150%)", extracted)

    # 5. Split jadi 4 bagian
    print("\n[TEST] Split jadi 4 bagian:")
    parts = {
        "top_left": (0, 0, width // 2, height // 2),
        "top_right": (width // 2, 0, width, height // 2),
        "bottom_left": (0, height // 2, width // 2, height),
        "bottom_right": (width // 2, height // 2, width, height),
    }
    for name, box in parts.items():
        part_img = original_image.crop(box)
        part_img.save(os.path.join(OUTPUT_DIR, f"part_{name}.png"))
        try:
            extracted = extract_message_lsb_from_pil_image(part_img)
        except Exception as e:
            extracted = f"[ERROR] {e}"
        log_check(f"Split part: {name}", extracted)

    # 6. Rotate variasi
    print("\n[TEST] Rotate variasi:")
    for angle in (90, 180, 270):
        rotated = rotate_image(original_image, angle)
        rotated.save(os.path.join(OUTPUT_DIR, f"rotated_{angle}.png"))
        try:
            extracted = extract_message_lsb_from_pil_image(rotated)
        except Exception as e:
            extracted = f"[ERROR] {e}"
        log_check(f"Rotate ({angle}°)", extracted)

    # Ringkasan hasil
    print("=" * 70)
    print("📊 RINGKASAN HASIL PENGUJIAN:")
    if SUCCESSFUL_TESTS:
        for t in SUCCESSFUL_TESTS:
            print(f"   ✅ {t} berhasil mengekstrak watermark")
    else:
        print("   ❌ Tidak ada kondisi yang berhasil")
    print("=" * 70)
    print(f"✅ Pengujian selesai. Hasil gambar tersimpan di '{OUTPUT_DIR}'.")


# ======================
# ENTRY POINT
# ======================
if __name__ == "__main__":
    unittest.main(exit=False)
    test_robustness()
