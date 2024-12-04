import pytest
from datetime import datetime
from fastapi import status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.post import Post, Tag
from app.models.user import User, UserRole


@pytest.fixture
def test_tags(db: Session):
    """Create test tags"""
    tags = [
        Tag(name="python"),
        Tag(name="fastapi"),
        Tag(name="testing")
    ]
    for tag in tags:
        db.add(tag)
    db.commit()
    for tag in tags:
        db.refresh(tag)
    return tags


@pytest.fixture
def test_post(db: Session, test_author: User, test_tags: list[Tag]):
    """Create a test post"""
    post = Post(
        title="Test Post",
        content="Test Content",
        author_id=test_author.id,
        tags=test_tags[:2],  # Add first two tags
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def test_create_post(author_client, test_tags):
    """Test creating a new post"""
    post_data = {
        "title": "Test Post",
        "content": "Test Content",
        "tags": ["python", "fastapi"]
    }

    response = author_client.post(
        f"{settings.API_V1_STR}/posts/",
        json=post_data
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == post_data["title"]
    assert data["content"] == post_data["content"]
    assert len(data["tags"]) == 2
    assert all(tag["name"] in ["python", "fastapi"] for tag in data["tags"])


def test_create_post_invalid_data(author_client):
    """Test creating a post with invalid data"""
    # Test with empty title
    response = author_client.post(
        f"{settings.API_V1_STR}/posts/",
        json={"title": "", "content": "Content", "tags": []}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test with empty content
    response = author_client.post(
        f"{settings.API_V1_STR}/posts/",
        json={"title": "Title", "content": "", "tags": []}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test with missing required fields
    response = author_client.post(
        f"{settings.API_V1_STR}/posts/",
        json={"tags": []}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_post_reader(authorized_client):
    """Test that readers cannot create posts"""
    post_data = {
        "title": "Test Post",
        "content": "Test Content",
        "tags": []
    }

    response = authorized_client.post(
        f"{settings.API_V1_STR}/posts/",
        json=post_data
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_posts(client, db, test_author, test_tags):
    """Test getting all posts"""
    # Create test posts
    posts = []
    for i in range(3):
        post = Post(
            title=f"Test Post {i}",
            content=f"Content {i}",
            author_id=test_author.id,
            tags=test_tags[:2],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(post)
        posts.append(post)
    db.commit()
    for post in posts:
        db.refresh(post)

    response = client.get(f"{settings.API_V1_STR}/posts/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 3
    for post_data in data:
        assert "title" in post_data
        assert "content" in post_data
        assert "created_at" in post_data
        assert "tags" in post_data


def test_get_posts_pagination(client, db, test_author):
    """Test post pagination"""
    # Create multiple posts
    for i in range(15):
        post = Post(
            title=f"Test Post {i}",
            content=f"Content {i}",
            author_id=test_author.id,
            tags=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(post)
    db.commit()

    # Test default pagination
    response = client.get(f"{settings.API_V1_STR}/posts/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 10  # Default limit

    # Test custom pagination
    response = client.get(f"{settings.API_V1_STR}/posts/?skip=10&limit=5")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 5


def test_get_post_by_id(client, test_post):
    """Test getting a single post by ID"""
    response = client.get(f"{settings.API_V1_STR}/posts/{test_post.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == test_post.title
    assert data["content"] == test_post.content
    assert len(data["tags"]) == 2


def test_get_post_not_found(client):
    """Test getting a non-existent post"""
    response = client.get(f"{settings.API_V1_STR}/posts/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_post(author_client, test_post, test_author, db):
    """Test updating a post"""
    # Make sure the test_post is owned by test_author
    test_post.author_id = test_author.id
    db.commit()

    update_data = {
        "title": "Updated Title",
        "content": "Updated Content",
        "tags": ["python", "testing"]
    }

    response = author_client.put(
        f"{settings.API_V1_STR}/posts/{test_post.id}",
        json=update_data
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["content"] == update_data["content"]
    assert len(data["tags"]) == 2
    assert all(tag["name"] in update_data["tags"] for tag in data["tags"])


def test_update_post_not_found(author_client):
    """Test updating a non-existent post"""
    update_data = {
        "title": "Updated Title",
        "content": "Updated Content",
        "tags": []
    }

    response = author_client.put(
        f"{settings.API_V1_STR}/posts/99999",
        json=update_data
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_post(author_client, test_post, test_author, db):
    """Test deleting a post"""
    # Make sure the test_post is owned by test_author
    test_post.author_id = test_author.id
    db.commit()

    response = author_client.delete(
        f"{settings.API_V1_STR}/posts/{test_post.id}"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Post deleted successfully"

    # Verify post is deleted
    response = author_client.get(f"{settings.API_V1_STR}/posts/{test_post.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_post_not_found(author_client):
    """Test deleting a non-existent post"""
    response = author_client.delete(
        f"{settings.API_V1_STR}/posts/99999"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_posts_with_filters(client, db, test_author, test_tags):
    """Test getting posts with various filters"""
    now = datetime.utcnow()

    # Create posts with different dates and tags
    posts = [
        Post(
            title="Python Tutorial",
            content="Python content",
            author_id=test_author.id,
            tags=[test_tags[0]],  # python tag
            created_at=now,
            updated_at=now
        ),
        Post(
            title="FastAPI Guide",
            content="FastAPI content",
            author_id=test_author.id,
            tags=[test_tags[1]],  # fastapi tag
            created_at=now,
            updated_at=now
        )
    ]
    for post in posts:
        db.add(post)
    db.commit()

    # Test keyword filter
    response = client.get(f"{settings.API_V1_STR}/posts/?keyword=python")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert "Python" in data[0]["title"]

    # Test tag filter
    response = client.get(f"{settings.API_V1_STR}/posts/?tag=fastapi")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert "FastAPI" in data[0]["title"]


def test_update_post_unauthorized(authorized_client, test_post):
    """Test updating post without proper authorization"""
    update_data = {
        "title": "Updated Title",
        "content": "Updated Content",
        "tags": []
    }

    response = authorized_client.put(
        f"{settings.API_V1_STR}/posts/{test_post.id}",
        json=update_data
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_post_unauthorized(authorized_client, test_post):
    """Test deleting post without proper authorization"""
    response = authorized_client.delete(
        f"{settings.API_V1_STR}/posts/{test_post.id}"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
