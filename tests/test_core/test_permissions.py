import pytest
from fastapi import HTTPException
from app.core.permissions import (
    Permission,
    check_permission,
    require_permission,
    ROLE_PERMISSIONS
)
from app.models.user import UserRole
from app.schemas.user import User as UserSchema
from app.models.post import Post as PostModel


@pytest.fixture
def mock_reader():
    """Create a mock reader user"""
    return UserSchema(
        id=1,
        email="reader@example.com",
        full_name="Test Reader",
        role=UserRole.READER,
        is_active=True
    )


@pytest.fixture
def mock_author():
    """Create a mock author user"""
    return UserSchema(
        id=2,
        email="author@example.com",
        full_name="Test Author",
        role=UserRole.AUTHOR,
        is_active=True
    )


@pytest.fixture
def mock_admin():
    """Create a mock admin user"""
    return UserSchema(
        id=3,
        email="admin@example.com",
        full_name="Test Admin",
        role=UserRole.ADMIN,
        is_active=True
    )


def test_admin_permissions(mock_admin):
    """Test that admin has all permissions"""
    for permission in Permission:
        assert check_permission(mock_admin, permission) is True


def test_author_permissions(mock_author):
    """Test author permissions"""
    # Authors should have post and comment permissions
    assert check_permission(mock_author, Permission.CREATE_POST) is True
    assert check_permission(mock_author, Permission.EDIT_POST) is True
    assert check_permission(mock_author, Permission.DELETE_POST) is True
    assert check_permission(mock_author, Permission.CREATE_COMMENT) is True
    assert check_permission(mock_author, Permission.EDIT_COMMENT) is True
    assert check_permission(mock_author, Permission.DELETE_COMMENT) is True

    # Authors should not have user management permissions
    assert check_permission(mock_author, Permission.MANAGE_USERS) is False


def test_reader_permissions(mock_reader):
    """Test reader permissions"""
    # Readers should have comment permissions
    assert check_permission(mock_reader, Permission.CREATE_COMMENT) is True
    assert check_permission(mock_reader, Permission.EDIT_COMMENT) is True
    assert check_permission(mock_reader, Permission.DELETE_COMMENT) is True

    # Readers should not have post management permissions
    assert check_permission(mock_reader, Permission.CREATE_POST) is False
    assert check_permission(mock_reader, Permission.EDIT_POST) is False
    assert check_permission(mock_reader, Permission.DELETE_POST) is False


def test_resource_ownership(mock_author):
    """Test permission checks with resource ownership"""
    # Author should be able to edit their own post
    assert check_permission(
        mock_author,
        Permission.EDIT_POST,
        resource_owner_id=mock_author.id
    ) is True

    # Author should not be able to edit someone else's post
    assert check_permission(
        mock_author,
        Permission.EDIT_POST,
        resource_owner_id=999
    ) is False


@pytest.mark.asyncio
async def test_require_permission_decorator():
    """Test the require_permission decorator"""
    @require_permission(Permission.CREATE_POST)
    async def test_endpoint(current_user: UserSchema):
        return {"message": "success"}

    # Test with admin user (should succeed)
    admin = UserSchema(
        id=1,
        email="admin@test.com",
        role=UserRole.ADMIN,
        is_active=True,
        full_name="Admin"
    )
    result = await test_endpoint(current_user=admin)
    assert result == {"message": "success"}

    # Test with reader user (should raise HTTPException)
    reader = UserSchema(
        id=2,
        email="reader@test.com",
        role=UserRole.READER,
        is_active=True,
        full_name="Reader"
    )
    with pytest.raises(HTTPException) as exc_info:
        await test_endpoint(current_user=reader)
    assert exc_info.value.status_code == 403


def test_inactive_user(mock_reader):
    """Test permissions for inactive user"""
    mock_reader.is_active = False
    for permission in Permission:
        assert check_permission(mock_reader, permission) is False


def test_role_permissions_completeness():
    """Test that all roles have defined permissions"""
    # Every role should have defined permissions
    for role in UserRole:
        assert role in ROLE_PERMISSIONS
        assert len(ROLE_PERMISSIONS[role]) > 0

    # Admin should have all permissions
    admin_permissions = set(ROLE_PERMISSIONS[UserRole.ADMIN])
    all_permissions = set(Permission)
    assert admin_permissions == all_permissions


def test_permission_inheritance():
    """Test that higher roles include lower role permissions"""
    reader_permissions = set(ROLE_PERMISSIONS[UserRole.READER])
    author_permissions = set(ROLE_PERMISSIONS[UserRole.AUTHOR])
    admin_permissions = set(ROLE_PERMISSIONS[UserRole.ADMIN])

    # Author should have all reader permissions
    assert reader_permissions.issubset(author_permissions)
    # Admin should have all author permissions
    assert author_permissions.issubset(admin_permissions)


@pytest.mark.asyncio
async def test_permission_decorator_with_resource():
    """Test permission decorator with resource ownership"""
    @require_permission(Permission.EDIT_POST)
    async def edit_post(current_user: UserSchema, post_id: int = None):
        return {"message": "success"}

    # Test with author editing own post
    author = UserSchema(
        id=1,
        email="author@test.com",
        role=UserRole.AUTHOR,
        is_active=True,
        full_name="Author"
    )
    result = await edit_post(current_user=author, post_id=1)
    assert result == {"message": "success"}

    # Test with author trying to edit another's post
    with pytest.raises(HTTPException) as exc_info:
        await edit_post(current_user=author, post_id=2)
    assert exc_info.value.status_code == 403


def test_admin_override(mock_admin, db):
    """Test that admin can override normal permission restrictions"""
    # Admin should be able to edit any post
    assert check_permission(
        mock_admin,
        Permission.EDIT_POST,
        resource_owner_id=999
    ) is True

    # Admin should be able to delete any post
    assert check_permission(
        mock_admin,
        Permission.DELETE_POST,
        resource_owner_id=999
    ) is True


def test_permission_edge_cases(mock_author):
    """Test edge cases in permission system"""
    # Test with None resource_owner_id
    assert check_permission(
        mock_author,
        Permission.EDIT_POST,
        resource_owner_id=None
    ) is True

    # Test with non-existent permission (should not break)
    assert check_permission(
        mock_author,
        "NON_EXISTENT_PERMISSION",  # type: ignore
        resource_owner_id=None
    ) is False


def test_permission_caching(mock_author):
    """Test that permission checks are consistent"""
    # Multiple checks should return the same result
    first_check = check_permission(mock_author, Permission.CREATE_POST)
    second_check = check_permission(mock_author, Permission.CREATE_POST)
    assert first_check == second_check

    # Changing user state should affect permissions
    mock_author.is_active = False
    inactive_check = check_permission(mock_author, Permission.CREATE_POST)
    assert inactive_check is False
