from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional


class UserBase(BaseModel):
    username: str
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = None
    profile_picture: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    name: str
    profile_picture: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


class UserPublic(BaseModel):
    id: UUID
    username: str
    profile_picture: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


class UserDelete(BaseModel):
    id: UUID

    model_config = {
        "from_attributes": True
    }
