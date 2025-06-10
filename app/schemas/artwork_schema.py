from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal
from typing import Optional

class ArtworkCreate(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    category: str | None = None
    license_type: str | None = None
    price: Decimal
    image_url: str
    unique_key: str
    hash: str
    user_id: UUID

    class Config:
        from_attributes = True

class ArtworkResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: str | None = None
    category: str | None = None
    license_type: str | None = None
    price: Decimal
    image_url: str
    unique_key: str
    hash: str

    class Config:
        from_attributes = True

class ArtworkUploadRequest(BaseModel):
    title: str
    category: str
    description: Optional[str] = None
    license_type: str