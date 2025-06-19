from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class LikeResponse(BaseModel):
    id: UUID
    artwork_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
