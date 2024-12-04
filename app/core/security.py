from datetime import datetime, timedelta
from datetime import timezone
from typing import Any, Dict, Optional, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.core.token_blacklist import token_blacklist

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create JWT access token

    Args:
        subject: Token subject (usually user email)
        expires_delta: Optional token expiration time
        additional_claims: Optional additional JWT claims

    Returns:
        JWT token string
    """
    if expires_delta is not None:
        expire = datetime.now(tz=timezone.utc) + expires_delta
    else:
        expire = datetime.now(tz=timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Base claims
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(tz=timezone.utc),
        "type": "access_token"
    }

    # Add any additional claims
    if additional_claims:
        to_encode.update(additional_claims)

    # Create token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify JWT token validity

    Args:
        token: JWT token string

    Returns:
        Dict containing token claims

    Raises:
        JWTError: If token is invalid
    """
    # Check if token is blacklisted
    if token_blacklist.is_blacklisted(token):
        raise jwt.JWTError("Token has been invalidated")

    # Decode and verify token
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )

    return payload


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password

    Raises:
        ValueError: If password is None
    """
    if password is None:
        raise ValueError("Password cannot be None")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to compare against

    Returns:
        bool: True if password matches, False otherwise

    Raises:
        ValueError: If either password is None
    """
    if plain_password is None or hashed_password is None:
        raise ValueError("Password and hash cannot be None")
    return pwd_context.verify(plain_password, hashed_password)


def invalidate_token(token: str) -> None:
    """
    Invalidate a token by adding it to the blacklist

    Args:
        token: JWT token to invalidate

    Raises:
        ValueError: If token is invalid
    """
    token_blacklist.blacklist_token(token)


def is_token_valid(token: str) -> bool:
    """
    Check if a token is valid and not blacklisted

    Args:
        token: JWT token to check

    Returns:
        bool: True if token is valid and not blacklisted, False otherwise
    """
    try:
        if token_blacklist.is_blacklisted(token):
            return False
        verify_token(token)
        return True
    except (jwt.JWTError, ValueError):
        return False
