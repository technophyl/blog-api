import pytest
from datetime import datetime, timedelta
from datetime import timezone
from jose import jwt, JWTError
from app.core.security import (
    create_access_token,
    verify_token,
    get_password_hash,
    verify_password,
    invalidate_token,
    is_token_valid
)
from app.core.config import settings
from app.core.token_blacklist import token_blacklist


@pytest.fixture(autouse=True)
def clear_redis():
    """Clear Redis after each test"""
    yield
    token_blacklist.redis_client.flushdb()


def test_create_access_token():
    """Test access token creation"""
    # Test with explicit expiration
    expires_delta = timedelta(minutes=15)
    token = create_access_token(
        subject="test@example.com",
        expires_delta=expires_delta
    )

    payload = jwt.decode(token, settings.SECRET_KEY,
                         algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "test@example.com"
    assert "exp" in payload
    assert payload["type"] == "access_token"

    # Test with default expiration
    token = create_access_token(subject="test@example.com")
    payload = jwt.decode(token, settings.SECRET_KEY,
                         algorithms=[settings.ALGORITHM])
    assert "exp" in payload


def test_create_access_token_with_claims():
    """Test access token creation with additional claims"""
    additional_claims = {"role": "admin", "permissions": ["read", "write"]}
    token = create_access_token(
        subject="test@example.com",
        additional_claims=additional_claims
    )

    payload = jwt.decode(token, settings.SECRET_KEY,
                         algorithms=[settings.ALGORITHM])
    assert payload["role"] == "admin"
    assert payload["permissions"] == ["read", "write"]


def test_verify_token():
    """Test token verification"""
    token = create_access_token(subject="test@example.com")
    payload = verify_token(token)
    assert payload["sub"] == "test@example.com"


def test_verify_token_expired():
    """Test verification of expired token"""
    token = create_access_token(
        subject="test@example.com",
        expires_delta=timedelta(minutes=-1)
    )

    with pytest.raises(JWTError):
        verify_token(token)


def test_verify_token_invalid():
    """Test verification of invalid token"""
    with pytest.raises(JWTError):
        verify_token("invalid_token")


def test_verify_token_blacklisted():
    """Test verification of blacklisted token"""
    token = create_access_token(subject="test@example.com")
    invalidate_token(token)

    with pytest.raises(JWTError):
        verify_token(token)


def test_password_hashing():
    """Test password hashing functionality"""
    password = "testpassword123"
    hashed = get_password_hash(password)

    # Verify hash is different from password
    assert hashed != password
    # Verify password verification works
    assert verify_password(password, hashed) is True
    # Verify wrong password fails
    assert verify_password("wrongpassword", hashed) is False


def test_password_hash_none():
    """Test password hashing with None value"""
    with pytest.raises(ValueError):
        get_password_hash(None)


def test_verify_password_none():
    """Test password verification with None values"""
    with pytest.raises(ValueError):
        verify_password(None, "hashedpassword")

    with pytest.raises(ValueError):
        verify_password("password", None)


def test_token_invalidation():
    """Test token invalidation"""
    token = create_access_token(subject="test@example.com")

    # Token should be valid initially
    assert is_token_valid(token) is True

    # Invalidate token
    invalidate_token(token)

    # Token should be invalid after blacklisting
    assert is_token_valid(token) is False


def test_is_token_valid():
    """Test token validation"""
    # Test valid token
    token = create_access_token(subject="test@example.com")
    assert is_token_valid(token) is True

    # Test expired token
    expired_token = create_access_token(
        subject="test@example.com",
        expires_delta=timedelta(minutes=-1)
    )
    assert is_token_valid(expired_token) is False

    # Test invalid token
    assert is_token_valid("invalid_token") is False

    # Test blacklisted token
    invalidate_token(token)
    assert is_token_valid(token) is False


def test_token_expiry_calculation():
    """Test token expiry time calculation"""
    expires_delta = timedelta(minutes=30)
    token = create_access_token(
        subject="test@example.com",
        expires_delta=expires_delta
    )

    payload = jwt.decode(token, settings.SECRET_KEY,
                         algorithms=[settings.ALGORITHM])
    exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(tz=timezone.utc)

    # Allow 5 seconds tolerance for test execution time
    assert abs((exp_time - now - expires_delta).total_seconds()) < 5


def test_password_verification_timing():
    """Test that password verification timing is consistent"""
    password = "testpassword123"
    hashed = get_password_hash(password)

    # Time verification of correct password
    start = datetime.now(tz=timezone.utc)
    verify_password(password, hashed)
    correct_time = (datetime.now(tz=timezone.utc) - start).total_seconds()

    # Time verification of wrong password
    start = datetime.now(tz=timezone.utc)
    verify_password("wrongpassword", hashed)
    wrong_time = (datetime.now(tz=timezone.utc) - start).total_seconds()

    # Verification times should be similar (within 100ms)
    assert abs(correct_time - wrong_time) < 0.1
