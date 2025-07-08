from fastapi import (
    APIRouter, Depends, HTTPException, status, UploadFile, File, Form
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.schemas.user_schema import UserResponse
from app.models.user import User
from app.api.deps import get_db
import uuid
import os
import shutil

router = APIRouter()
UPLOAD_DIR = "profile_uploads"


@router.post("/register", response_model=UserResponse)
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = uuid.uuid4()
    filename = None

    if file:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filename = f"{user_id}_{file.filename}"
        with open(os.path.join(UPLOAD_DIR, filename), "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    new_user = User(
        id=user_id,
        username=username,
        email=email,
        password=password,  
        profile_picture=filename
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/{user_id}/profile-picture")
def get_profile_picture(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.profile_picture:
        raise HTTPException(status_code=404, detail="Profile picture not found")

    file_path = os.path.join(UPLOAD_DIR, user.profile_picture)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return StreamingResponse(open(file_path, "rb"), media_type="image/jpeg")


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        return db_user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pengguna tidak ditemukan")


@router.get("/", response_model=list[UserResponse])
def get_all_users(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()
