from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user_schema import UserCreate, UserLogin, UserResponse
from app.models.user import User
from app.services.hashing import hash_password, verify_password
from app.api.deps import get_db
from jose import jwt
from datetime import datetime, timedelta
from app.core.config import settings

router = APIRouter() 

@router.post("/register", response_model=UserResponse)  
def register(user: UserCreate, db: Session = Depends(get_db)):
    print("ini user", user)
    user_exist = db.query(User).filter(User.email == user.email).first()
    if user_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    print('user_exist', user_exist)
    hashed_pw = hash_password(user.password)
    print(hashed_pw)
    new_user = User(
        username=user.username,
        name=user.name,
        email=user.email,
        password_hash=hashed_pw,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        name=new_user.name,
        password_hash=new_user.password_hash
    )

@router.post("/login")
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user.id),
        "exp": int((datetime.utcnow() + access_token_expires).timestamp())
    }
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}