import os
import imagehash
from PIL import Image
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim
import logging
import torch
import torchvision.transforms as transforms
from torchvision.models import resnet18, ResNet18_Weights
from imagehash import average_hash, phash, dhash, whash

model = resnet18(weights=None)

_restnet_model = resnet18(weights=ResNet18_Weights.DEFAULT)
_restnet_model.eval()


_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

logger = logging.getLogger(__name__)

def compute_all_hashes(pil_image: Image.Image) -> dict:
    return {
        "ahash": str(average_hash(pil_image)),
        "phash": str(phash(pil_image)),
        "dhash": str(dhash(pil_image)),
        "whash": str(whash(pil_image))
    }

def hamming_dist(h1, h2):
    return sum(c1 != c2 for c1, c2 in zip(h1, h2))


def is_similar_by_hash(hash1: str, hash2: str, threshold: int = 5) -> bool:
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2)) <= threshold

    for key in thresholds.keys():
        db_hash = getattr(artwork_db, f"hash_{key}" if key != "ahash" else "hash")
        if db_hash:
            dist = hamming_dist(uploaded_hashes[key], db_hash)
            if dist <= thresholds[key]:
                return True
    return False

def is_similar_by_ssim(pil_image: Image.Image, image_path: str, threshold: float = 0.92) -> bool:
    try:
        img1 = np.array(pil_image.resize((256, 256)).convert("L"))
        img2 = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.resize(img2, (256, 256))
        from skimage.metrics import structural_similarity as ssim
        score, _ = ssim(img1, img2, full=True)
        return score > threshold
    except:
        return False

def is_similar_by_orb(pil_image: Image.Image, image_path: str, threshold: int = 25) -> bool:
    try:
        orb = cv2.ORB_create()
        img1 = cv2.cvtColor(np.array(pil_image.resize((256, 256))), cv2.COLOR_RGB2GRAY)
        img2 = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.resize(img2, (256, 256))

        kp1, des1 = orb.detectAndCompute(img1, None)
        kp2, des2 = orb.detectAndCompute(img2, None)

        if des1 is None or des2 is None:
            return False

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)

        return len(matches) > threshold
    except:
        return False

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)

    good_matches = [m for m in matches if m.distance < 60]
    similarity = len(good_matches) / max(len(kp1), len(kp2))

    return similarity > threshold

def is_similar_image(uploaded_hashes: dict, pil_image: Image.Image, artwork_db) -> bool:
    # Deteksi hash mirip (minimal 2 dari 4 hash serupa)
    thresholds = {"ahash": 2, "phash": 2, "dhash": 2, "whash": 2}
    similar_hash_count = 0

    for key, threshold in thresholds.items():
        db_hash = getattr(artwork_db, f"hash_{key}" if key != "ahash" else "hash")
        if db_hash:
            dist = hamming_dist(uploaded_hashes[key], db_hash)
            if dist <= threshold:
                similar_hash_count += 1

    if similar_hash_count >= 2:
        logger.info(f"Deteksi duplikat via HASH: {artwork_db.title}")
        return True

    # Deteksi visual (SSIM atau ORB)
    db_img_path = os.path.join("public", artwork_db.image_url.lstrip("/"))
    if os.path.exists(db_img_path):
        if is_similar_by_ssim(pil_image, db_img_path):
            logger.info(f"Deteksi duplikat via SSIM: {artwork_db.title}")
            return True
        if is_similar_by_orb(pil_image, db_img_path):
            logger.info(f"Deteksi duplikat via ORB: {artwork_db.title}")
            return True

    return False
