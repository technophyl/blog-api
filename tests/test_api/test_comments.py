import pytest
from datetime import datetime
from fastapi import status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.comment import Comment
from app.models.post import Post
from app.models.user import User, UserRole


@pytest.fixture
def test_post(db: Session, test_author: User):
    """Create a test post"""
    post = Post(
        title="Test Post",
        content="Test Content",
        author_id=test_author.id,
        tags=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@pytest.fixture
def test_comment(db: Session, test_post: Post, test_user: User):
    """Create a test comment"""
    comment = Comment(
        content="Test Comment",
        post_id=test_post.id,
        author_id=test_user.id,
        created_at=datetime.utcnow()
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def test_create_comment(authorized_client, test_post):
    """Test creating a new comment"""
    comment_data = {
        "content": "New Comment",
        "post_id": test_post.id
    }

    response = authorized_client.post(
        f"{settings.API_V1_STR}/comments/",
        json=comment_data
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["content"] == comment_data["content"]
    assert data["post_id"] == comment_data["post_id"]
    assert "created_at" in data
    assert "id" in data


def test_create_comment_invalid_data(authorized_client, test_post):
    """Test creating a comment with invalid data"""
    # Test with empty content
    response = authorized_client.post(
        f"{settings.API_V1_STR}/comments/",
        json={"content": "", "post_id": test_post.id}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test with missing post_id
    response = authorized_client.post(
        f"{settings.API_V1_STR}/comments/",
        json={"content": "Test Comment"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_comment_non_existent_post(authorized_client):
    """Test creating a comment for a non-existent post"""
    comment_data = {
        "content": "New Comment",
        "post_id": 99999
    }

    response = authorized_client.post(
        f"{settings.API_V1_STR}/comments/",
        json=comment_data
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_comments_by_post(client, test_post, test_comment):
    """Test getting all comments for a specific post"""
    response = client.get(
        f"{settings.API_V1_STR}/comments/post/{test_post.id}"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["content"] == test_comment.content
    assert data[0]["post_id"] == test_post.id
    assert "created_at" in data[0]


def test_get_comments_pagination(client, db, test_post, test_user):
    """Test comment pagination"""
    # Create multiple comments
    for i in range(15):
        comment = Comment(
            content=f"Test Comment {i}",
            post_id=test_post.id,
            author_id=test_user.id,
            created_at=datetime.utcnow()
        )
        db.add(comment)
    db.commit()

    # Test with default pagination
    response = client.get(
        f"{settings.API_V1_STR}/comments/post/{test_post.id}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 10  # Default limit

    # Test with custom pagination
    response = client.get(
        f"{settings.API_V1_STR}/comments/post/{test_post.id}?skip=10&limit=5"
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 5


def test_update_comment(authorized_client, test_comment):
    """Test updating a comment"""
    update_data = {
        "content": "Updated Comment Content"
    }

    response = authorized_client.put(
        f"{settings.API_V1_STR}/comments/{test_comment.id}",
        json=update_data
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["content"] == update_data["content"]
    assert data["id"] == test_comment.id


def test_update_comment_not_found(authorized_client):
    """Test updating a non-existent comment"""
    update_data = {
        "content": "Updated Content"
    }

    response = authorized_client.put(
        f"{settings.API_V1_STR}/comments/99999",
        json=update_data
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_comment_unauthorized(client, test_comment):
    """Test updating a comment without authorization"""
    update_data = {
        "content": "Updated Content"
    }

    response = client.put(
        f"{settings.API_V1_STR}/comments/{test_comment.id}",
        json=update_data
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_comment(authorized_client, test_comment):
    """Test deleting a comment"""
    response = authorized_client.delete(
        f"{settings.API_V1_STR}/comments/{test_comment.id}"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Comment deleted successfully"


def test_delete_comment_not_found(authorized_client):
    """Test deleting a non-existent comment"""
    response = authorized_client.delete(
        f"{settings.API_V1_STR}/comments/99999"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_comment_unauthorized(client, test_comment):
    """Test deleting a comment without authorization"""
    response = client.delete(
        f"{settings.API_V1_STR}/comments/{test_comment.id}"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_comment_by_different_role_users(
    client, db, test_post, test_users
):
    """Test comment operations with different user roles"""
    # Login as different users and test commenting
    for role, user in test_users.items():
        # Login
        response = client.post(
            f"{settings.API_V1_STR}/auth/login",
            data={"username": user.email, "password": f"{role}pass"}
        )
        assert response.status_code == status.HTTP_200_OK
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to create a comment
        comment_data = {
            "content": f"Comment by {role}",
            "post_id": test_post.id
        }
        response = client.post(
            f"{settings.API_V1_STR}/comments/",
            json=comment_data,
            headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
