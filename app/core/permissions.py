from enum import Enum
from functools import wraps
from fastapi import HTTPException, status, Depends
from app.api import deps
from app.schemas.user import User
from app.models.user import UserRole
from app.models.post import Post as PostModel


class Permission(str, Enum):
    CREATE_POST = "create_post"
    EDIT_POST = "edit_post"
    DELETE_POST = "delete_post"
    CREATE_COMMENT = "create_comment"
    EDIT_COMMENT = "edit_comment"
    DELETE_COMMENT = "delete_comment"
    MANAGE_USERS = "manage_users"


ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.CREATE_POST,
        Permission.EDIT_POST,
        Permission.DELETE_POST,
        Permission.CREATE_COMMENT,
        Permission.EDIT_COMMENT,
        Permission.DELETE_COMMENT,
        Permission.MANAGE_USERS
    ],
    UserRole.AUTHOR: [
        Permission.CREATE_POST,
        Permission.EDIT_POST,
        Permission.DELETE_POST,
        Permission.CREATE_COMMENT,
        Permission.EDIT_COMMENT,
        Permission.DELETE_COMMENT
    ],
    UserRole.READER: [
        Permission.CREATE_COMMENT,
        Permission.EDIT_COMMENT,
        Permission.DELETE_COMMENT
    ]
}


def check_permission(user: User, permission: Permission, resource_owner_id: int = None) -> bool:
    """
    Check if a user has the required permission.
    For certain operations, also validates resource ownership.
    """
    if user.is_active == False:
        return False

    if user.role == UserRole.ADMIN:
        return True

    if permission not in ROLE_PERMISSIONS[user.role]:
        return False

    # Check resource ownership for edit/delete operations
    if resource_owner_id and permission in [
        Permission.EDIT_POST,
        Permission.DELETE_POST,
        Permission.EDIT_COMMENT,
        Permission.DELETE_COMMENT
    ]:
        return user.id == resource_owner_id

    return True


def require_permission(permission: Permission):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(deps.get_current_user), **kwargs):
            resource_owner_id = None
            if 'post_id' in kwargs:
                db = next(deps.get_db())
                post = db.query(PostModel).filter(
                    PostModel.id == kwargs['post_id']).first()
                if post:
                    resource_owner_id = post.author_id
            if not check_permission(current_user, permission, resource_owner_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User does not have permission: {permission}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
