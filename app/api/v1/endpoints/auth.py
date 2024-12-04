from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import timedelta
from app.api import deps
from app.core import security
from app.core.config import settings
from app.schemas.user import UserCreate, User, Token
from app.models.user import User as UserModel
from app.core.token_blacklist import token_blacklist
from typing import Any

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login")


@router.post("/register", response_model=User)
async def register(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
) -> Any:
    """Register a new user"""
    user = db.query(UserModel).filter(UserModel.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system."
        )
    user = UserModel(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """OAuth2 compatible token login"""
    user = db.query(UserModel).filter(
        UserModel.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email,
        expires_delta=access_token_expires,
        additional_claims={"role": user.role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    token: str = Security(oauth2_scheme)
) -> dict:
    """Logout user by blacklisting their token"""
    try:
        token_blacklist.blacklist_token(token)
        return {"message": "Successfully logged out"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.post("/test-token", response_model=User)
async def test_token(current_user: User = Depends(deps.get_current_user)) -> Any:
    """Test access token"""
    return current_user


@router.post("/reset-password/{email}")
async def reset_password(
    email: str,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Password Recovery endpoint.
    Note: This is a simplified version. In production, you would:
    1. Generate a password reset token
    2. Send it to user's email
    3. Create a separate endpoint to accept the reset token and new password
    """
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system."
        )

    # In production, implement password reset logic here
    return {"message": "Password reset email sent"}
