from typing import Generator
from sqlalchemy.orm import Session
from app.db.database import SessionLocal 
from fastapi import Depends, HTTPException, status  
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError 
from app.core.config import settings
from app.models.user import User 
import uuid 

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

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

    user_id: uuid.UUID = None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        user_id_str: str = payload.get("sub") 

        if user_id_str is None:
            raise credentials_exception

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    if user_id is None: 
        raise credentials_exception

 
    user = db.query(User).filter(User.id == user_id).first() 

    if user is None:
        raise credentials_exception

    return user