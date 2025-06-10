from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: EmailStr
    name: str
    password: str
    password_hash: str

class UserCreate(BaseModel):
    username: str
    name: str
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr

class UserSchema(BaseModel):
    id: int
    username: str
    email: str
    password_hash: str

    model_config = {
        "from_attributes": True
    }

class UserDelete(BaseModel):
    id: int

    # class Config:
    #     orm_mode = True
    
    model_config = {
        "from_attributes": True
    }
