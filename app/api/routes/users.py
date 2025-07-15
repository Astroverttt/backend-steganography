from fastapi import (
    APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
)
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from app.schemas.user_schema import UserResponse, UserLogin, UserUpdate
from app.models.user import User
from app.api.deps import get_db
from passlib.hash import bcrypt
import uuid
import os
import shutil

router = APIRouter()    

UPLOAD_DIR = "static/profile_pictures"
BASE_URL = "/static/profile_pictures"  


@router.post("/register", response_model=UserResponse)
async def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = uuid.uuid4()
    profile_picture_url = None

    if file:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filename = f"{user_id}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        profile_picture_url = f"{request.base_url}{BASE_URL}/{filename}"

    new_user = User(
        id=user_id,
        username=username,
        email=email,
        name=name,
        password_hash=bcrypt.hash(password),
        profile_picture=profile_picture_url
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse.model_validate(new_user)

@router.post("/login", response_model=UserResponse)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="Email tidak ditemukan")

    if not bcrypt.verify(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Password salah")

    return UserResponse.model_validate(db_user)


@router.patch("/{user_id}/profile-picture", response_model=UserResponse)
async def update_profile_picture(
    user_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if user.profile_picture:
        old_filename = user.profile_picture.split("/")[-1]
        old_path = os.path.join(UPLOAD_DIR, old_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    new_filename = f"{user_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    user.profile_picture = f"{request.base_url}{BASE_URL}/{new_filename}"
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(db_user)

@router.put("/{user_id}")
def update_user(user_id: uuid.UUID, update: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.username = db_user.username
    if update.username:
        db_user.username = update.username

    db.commit()
    db.refresh(db_user)

    return db_user


@router.get("/", response_model=list[UserResponse])
def get_all_users(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    users = db.query(User).offset(skip).limit(limit).all()
    return [UserResponse.model_validate(user) for user in users]
