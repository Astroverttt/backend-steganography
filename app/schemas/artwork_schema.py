from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal
from typing import Optional, List
from datetime import datetime


class ArtworkCreate(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    license_type: Optional[str] = None
    price: Decimal
    image_url: str
    unique_key: str
    hash: str
    user_id: UUID

    model_config = {
        "from_attributes": True
    }


class ArtworkResponse(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    license_type: Optional[str] = None
    price: Decimal
    image_url: str
    unique_key: str
    hash: str

    model_config = {
        "from_attributes": True
    }

class UserInfo(BaseModel):
    username: str
    profile_picture: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

class ArtworkUploadRequest(BaseModel):
    title: str
    category: str
    description: Optional[str] = None
    license_type: str
    price: Decimal = Decimal("0.0")


class ArtworkListResponse(BaseModel):
    status: str
    message: str
    result: List[ArtworkResponse]
    total: int
