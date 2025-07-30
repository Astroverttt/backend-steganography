from fastapi import (
    APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
)
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from app.schemas.user_schema import UserResponse, UserLogin, UserUpdate
from app.models.user import User
from app.api.deps import get_db, get_current_user
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

        profile_picture_url = f"{request.url.scheme}://{request.url.netloc}{BASE_URL}/{filename}"

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

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(db_user)


@router.put("/{user_id}", response_model=UserResponse) # Tambahkan response_model
def update_user(user_id: uuid.UUID, update: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = update.model_dump(exclude_unset=True) # Menggunakan model_dump untuk pydantic v2
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)

    return UserResponse.model_validate(db_user) # Pastikan mengembalikan model yang divalidasi


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if str(db_user.id) != str(current_user.id): # Membandingkan UUID sebagai string untuk keamanan
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user")

    if db_user.profile_picture:
        filename = os.path.basename(db_user.profile_picture)
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.get("/", response_model=list[UserResponse])
def get_all_users(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    users = db.query(User).offset(skip).limit(limit).all()
    return [UserResponse.model_validate(user) for user in users]