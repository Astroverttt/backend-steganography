import imagehash
from PIL import Image
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim

def compute_all_hashes(pil_image):
    return {
        "ahash": str(imagehash.average_hash(pil_image)),
        "phash": str(imagehash.phash(pil_image)),
        "dhash": str(imagehash.dhash(pil_image)),
        "whash": str(imagehash.whash(pil_image)),
    }

def is_similar_by_hash(uploaded_hashes, artwork):
    threshold = 2
    try:
        return (
            imagehash.hex_to_hash(artwork.hash_phash) - imagehash.hex_to_hash(uploaded_hashes["phash"]) <= threshold or
            imagehash.hex_to_hash(artwork.hash_dhash) - imagehash.hex_to_hash(uploaded_hashes["dhash"]) <= threshold or
            imagehash.hex_to_hash(artwork.hash_whash) - imagehash.hex_to_hash(uploaded_hashes["whash"]) <= threshold
        )
    except Exception:
        return False

def is_similar_by_ssim(uploaded_image_pil, db_image_path):
    try:
        uploaded_cv = cv2.cvtColor(np.array(uploaded_image_pil), cv2.COLOR_RGB2GRAY)
        db_cv = cv2.imread(db_image_path, cv2.IMREAD_GRAYSCALE)
        if db_cv is None:
            return False
        uploaded_cv = cv2.resize(uploaded_cv, (db_cv.shape[1], db_cv.shape[0]))
        score, _ = ssim(uploaded_cv, db_cv, full=True)
        return score > 0.92
    except Exception:
        return False
