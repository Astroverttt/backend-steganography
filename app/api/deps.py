from typing import Generator
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError 
from app.core.config import settings
from app.models.user import User 

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
   
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
 
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # 'sub' (subject) biasanya berisi identifier unik pengguna, seperti email atau username
        username: str = payload.get("sub") 
        if username is None:
            raise credentials_exception
    except JWTError:
        # Jika ada masalah saat mendekode token (misalnya, token tidak valid atau kadaluarsa)
        raise credentials_exception
    
    # Cari pengguna di database berdasarkan username (email)
    # Asumsi: kolom email di model User adalah yang digunakan sebagai username
    user = db.query(User).filter(User.email == username).first()
    if user is None:
        # Jika pengguna tidak ditemukan di database
        raise credentials_exception
    
    # Mengembalikan objek User jika token valid dan pengguna ditemukan
    return user

# Anda bisa menambahkan fungsi dependensi lain di sini jika diperlukan,
# misalnya untuk memeriksa apakah pengguna aktif atau memiliki peran tertentu.
# Contoh:
# async def get_current_active_user(current_user: User = Depends(get_current_user)):
#     if not current_user.is_active: # Contoh, jika User model memiliki properti is_active
#         raise HTTPException(status_code=400, detail="Inactive user")
#     return current_user
