from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from typing import List
from app.api import deps
from app.core.permissions import Permission, require_permission
from app.models.user import UserRole, User

router = APIRouter()


@router.get("/", response_model=List[User])
@require_permission(Permission.MANAGE_USERS)
async def get_users(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> List[User]:
    return db.query(User).all()


@router.put("/{user_id}/role", response_model=User)
@require_permission(Permission.MANAGE_USERS)
async def update_user_role(
    user_id: int,
    new_role: UserRole,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = new_role
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
