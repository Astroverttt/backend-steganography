from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app import models, schemas  # Pastikan Anda menggunakan ini
from app.db.database import SessionLocal
from typing import Generator, Optional  # Import Optional
from app.core.config import settings  # Gunakan settings untuk SECRET_KEY dan ALGORITHM

bearer_scheme = HTTPBearer()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Depends(bearer_scheme), db: Session = Depends(get_db)
) -> models.user.User:  # Anotasi tipe yang benar
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_value: str = token.credentials #ekstrak nilai token

    try:
        payload = jwt.decode(
            token_value,  # Gunakan token_value
            settings.SECRET_KEY,  # Gunakan dari settings
            algorithms=[settings.ALGORITHM],  # Gunakan dari settings
        )
        user_id: Optional[str] = payload.get("sub")  # sub berisi user_id, dan bisa saja None
        if user_id is None:
            raise credentials_exception
        # Di sini, Anda mungkin ingin memvalidasi klaim lain dalam payload (misalnya, exp)
    except JWTError as e:
        print(f"JWT Error: {e}") # Tambahkan logging error
        raise credentials_exception
    except Exception as e: # Tangkap semua exception
        print(f"Unexpected error during token validation: {e}")
        raise credentials_exception

    user: Optional[models.user.User] = ( #tipedata
        db.query(models.user.User).filter(models.user.User.id == user_id).first()
    )
    if user is None:
        raise credentials_exception
    return user
