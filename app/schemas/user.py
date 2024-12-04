from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from app.models.user import UserRole


class UserBase(BaseModel):
    """Base User Schema"""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user"""
    password: str
    role: Optional[UserRole] = UserRole.READER


class UserUpdate(UserBase):
    """Schema for updating a user"""
    password: Optional[str] = None


class User(UserBase):
    """Schema for user response"""
    id: int
    role: UserRole
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Schema for access token response"""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema for token payload"""
    sub: Optional[str] = None
    type: str


class Tokens(Token):
    """Schema for both access and refresh tokens"""
    pass


class TokenData(BaseModel):
    """Schema for decoded token data"""
    email: Optional[str] = None
