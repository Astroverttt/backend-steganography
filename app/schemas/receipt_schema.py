from pydantic import BaseModel
from datetime import datetime

class ReceiptDetailResponse(BaseModel):
    receipt_id: str
    artwork_title: str
    image_url: str
    purchase_date: datetime
    price: float
    buyer_secret_code: str
    download_url: str
    watermark_api: str
