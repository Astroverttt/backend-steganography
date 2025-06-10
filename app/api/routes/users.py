from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user_schema import UserResponse, UserUpdate
from app.models.user import User 
from app.api.deps import get_db

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        return db_user
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pengguna tidak ditemukan")

@router.get("/", response_model=list[UserResponse])
def get_all_users(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    users = db.query(User).offset(skip).limit(limit).all()
    return users