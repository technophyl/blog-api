import pytest
from fastapi import status
from jose import jwt
from datetime import timedelta
from app.core.config import settings
from app.models.user import UserRole
from app.core.token_blacklist import token_blacklist
from app.core import security


@pytest.fixture(autouse=True)
def clean_redis():
    """Clean Redis test database before each test"""
    token_blacklist.redis_client.select(1)  # Use test database
    token_blacklist.redis_client.flushdb()  # Clean before test
    yield
    token_blacklist.redis_client.flushdb()  # Clean after test


def test_create_user(client):
    """Test user registration"""
    response = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "newpass123",
            "full_name": "New User",
            "role": UserRole.READER
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert "password" not in data


def test_create_duplicate_user(client, test_user):
    """Test creating user with existing email"""
    response = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": test_user.email,
            "password": "anotherpass123",
            "full_name": "Another User",
            "role": UserRole.READER
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_success(client, test_user):
    """Test successful login"""
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={
            "username": test_user.email,
            "password": "testpass123"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify token
    token = data["access_token"]
    payload = jwt.decode(token, settings.SECRET_KEY,
                         algorithms=[settings.ALGORITHM])
    assert payload["sub"] == test_user.email


def test_login_incorrect_password(client, test_user):
    """Test login with wrong password"""
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={
            "username": test_user.email,
            "password": "wrongpass"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout(author_client):
    """Test logout functionality with author permissions"""
    # First request should succeed (author can create posts)
    post_data = {
        "title": "Test Post",
        "content": "Test Content",
        "tags": []
    }
    response = author_client.post(
        f"{settings.API_V1_STR}/posts/",
        json=post_data
    )
    assert response.status_code == status.HTTP_200_OK

    # Logout
    response = author_client.post(f"{settings.API_V1_STR}/auth/logout")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Successfully logged out"

    # Subsequent post request should fail after logout
    response = author_client.post(
        f"{settings.API_V1_STR}/posts/",
        json=post_data
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_invalid_token(client):
    """Test logout with invalid token"""
    response = client.post(
        f"{settings.API_V1_STR}/auth/logout",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_access_protected_endpoint(author_client):
    """Test accessing protected endpoint"""
    post_data = {
        "title": "Test Post",
        "content": "Test Content",
        "tags": []
    }
    response = author_client.post(
        f"{settings.API_V1_STR}/posts/",
        json=post_data
    )
    assert response.status_code == status.HTTP_200_OK


def test_access_protected_endpoint_no_token(client):
    """Test accessing protected endpoint without token"""
    post_data = {
        "title": "Test Post",
        "content": "Test Content",
        "tags": []
    }
    response = client.post(
        f"{settings.API_V1_STR}/posts/",
        json=post_data
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_access_protected_endpoint_expired_token(client, test_user):
    """Test accessing protected endpoint with expired token"""
    # Create expired token
    access_token = security.create_access_token(
        subject=test_user.email,
        expires_delta=timedelta(minutes=-1)
    )

    post_data = {
        "title": "Test Post",
        "content": "Test Content",
        "tags": []
    }
    response = client.post(
        f"{settings.API_V1_STR}/posts/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=post_data
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_test_token_endpoint(authorized_client, test_user):
    """Test the test-token endpoint"""
    response = authorized_client.post(f"{settings.API_V1_STR}/auth/test-token")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == test_user.email


@pytest.mark.parametrize(
    "role,expected_status",
    [
        (UserRole.ADMIN, status.HTTP_200_OK),
        (UserRole.AUTHOR, status.HTTP_200_OK),
        (UserRole.READER, status.HTTP_200_OK),
    ],
)
def test_role_based_access(client, test_users, role, expected_status):
    """Test access based on user role"""
    user = test_users[role.lower()]
    # Login
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={
            "username": user.email,
            "password": f"{role.lower()}pass"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    token = response.json()["access_token"]

    # Test access
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(f"{settings.API_V1_STR}/posts/", headers=headers)
    assert response.status_code == expected_status


def test_inactive_user_login(client, test_user, db):
    """Test that inactive users cannot login"""
    # Make user inactive
    test_user.is_active = False
    db.add(test_user)
    db.commit()

    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={
            "username": test_user.email,
            "password": "testpass123"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
