import os
import sys
import pytest
import asyncio
from typing import Generator, Dict
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.core.token_blacklist import token_blacklist
from app.core.config import settings
from app.core import security
from app.models.user import User, UserRole
from app.database import Base
from app.api.deps import get_db
from app.main import app

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get the absolute path to the test directory
TEST_DIR = os.path.dirname(os.path.abspath(__file__))

# Use in-memory SQLite for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine with SQLite
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool  # Use StaticPool for in-memory database
)

# Create test session
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_redis():
    """Setup test Redis connection"""
    # Use database 1 for testing (database 0 is default for production)
    token_blacklist.redis_client.select(1)

    yield

    # Cleanup after tests
    token_blacklist.redis_client.flushdb()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Provide test database session"""
    # Create all tables for each test
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after each test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Provide test client"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db: Session) -> User:
    """Create a test user"""
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password=security.get_password_hash("testpass123"),
        role=UserRole.READER,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_author(db: Session) -> User:
    """Create a test author user"""
    author = User(
        email="author@example.com",
        full_name="Test Author",
        hashed_password=security.get_password_hash("authorpass123"),
        role=UserRole.AUTHOR,
        is_active=True
    )
    db.add(author)
    db.commit()
    db.refresh(author)
    return author


@pytest.fixture(scope="function")
def authorized_client(client: TestClient, test_user: User) -> TestClient:
    """Create a test client with authorization"""
    login_data = {
        "username": test_user.email,
        "password": "testpass123"
    }
    response = client.post(
        f"{settings.API_V1_STR}/auth/login", data=login_data)
    token = response.json()["access_token"]
    client.headers = {
        "Authorization": f"Bearer {token}",
        **client.headers
    }
    return client


@pytest.fixture(scope="function")
def author_client(client: TestClient, test_author: User) -> TestClient:
    """Create a test client with author authorization"""
    login_data = {
        "username": test_author.email,
        "password": "authorpass123"
    }
    response = client.post(
        f"{settings.API_V1_STR}/auth/login", data=login_data)
    token = response.json()["access_token"]
    client.headers = {
        "Authorization": f"Bearer {token}",
        **client.headers
    }
    return client


@pytest.fixture(scope="function")
def test_users(db: Session) -> Dict[str, User]:
    """Create test users with different roles"""
    users = {
        "admin": User(
            email="admin@example.com",
            full_name="Admin User",
            hashed_password=security.get_password_hash("adminpass"),
            role=UserRole.ADMIN,
            is_active=True
        ),
        "author": User(
            email="author2@example.com",
            full_name="Author User",
            hashed_password=security.get_password_hash("authorpass"),
            role=UserRole.AUTHOR,
            is_active=True
        ),
        "reader": User(
            email="reader@example.com",
            full_name="Reader User",
            hashed_password=security.get_password_hash("readerpass"),
            role=UserRole.READER,
            is_active=True
        )
    }

    for user in users.values():
        db.add(user)
    db.commit()

    for key in users:
        db.refresh(users[key])

    return users
