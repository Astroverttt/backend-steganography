from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.user import User
from uuid import UUID
import shutil
import os

router = APIRouter()

@router.post("/users/{user_id}/upload-profile-picture")
async def upload_profile_picture(
    user_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    filename = f"{user_id}_{file.filename}"
    relative_path = f"profile_pictures/{filename}"
    full_path = os.path.join(relative_path)

    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    user.profile_picture = f"/api/media/{relative_path}"
    db.commit()

    return {
        "message": "Profile picture uploaded successfully",
        "profile_picture": user.profile_picture
    }

@router.get("/api/media/profile_pictures/{filename}")
def get_profile_picture(filename: str):
    file_path = os.path.join("profile_uploads", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
