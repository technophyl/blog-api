from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api import deps
from app.core.permissions import Permission, require_permission, check_permission
from app.models.user import User, UserRole
from app.schemas.comment import Comment, CommentCreate, CommentUpdate
from app.models.comment import Comment as CommentModel
from app.models.post import Post as PostModel

router = APIRouter()


@router.post("/", response_model=Comment)
@require_permission(Permission.CREATE_COMMENT)
async def create_comment(
    *,
    db: Session = Depends(deps.get_db),
    comment_in: CommentCreate,
    current_user: User = Depends(deps.get_current_user)
) -> Comment:
    """Create a new comment on a post."""
    # Check if post exists
    post = db.query(PostModel).filter(
        PostModel.id == comment_in.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comment = CommentModel(
        content=comment_in.content,
        post_id=comment_in.post_id,
        author_id=current_user.id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/{comment_id}", response_model=Comment)
async def get_comment(
    comment_id: int,
    db: Session = Depends(deps.get_db)
) -> Comment:
    comment = db.query(CommentModel).filter(
        CommentModel.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


@router.get("/post/{post_id}", response_model=List[Comment])
async def get_comments_by_post(
    post_id: int,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 10
) -> List[Comment]:
    """Get all comments for a specific post."""
    # Check if post exists
    post = db.query(PostModel).filter(PostModel.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comments = db.query(CommentModel)\
        .filter(CommentModel.post_id == post_id)\
        .offset(skip)\
        .limit(limit)\
        .all()
    return comments


@router.put("/{comment_id}", response_model=Comment)
@require_permission(Permission.EDIT_COMMENT)
async def update_comment(
    *,
    db: Session = Depends(deps.get_db),
    comment_id: int,
    comment_in: CommentUpdate,
    current_user: User = Depends(deps.get_current_user)
) -> Comment:
    """Update a specific comment."""
    comment = db.query(CommentModel).filter(
        CommentModel.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check if user has permission to edit this specific comment
    if not check_permission(current_user, Permission.EDIT_COMMENT, comment.author_id):
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions to edit this comment"
        )

    comment.content = comment_in.content
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/{comment_id}")
@require_permission(Permission.DELETE_COMMENT)
async def delete_comment(
    *,
    db: Session = Depends(deps.get_db),
    comment_id: int,
    current_user: User = Depends(deps.get_current_user)
) -> dict:
    """Delete a specific comment."""
    comment = db.query(CommentModel).filter(
        CommentModel.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check if user has permission to delete this specific comment
    if not check_permission(current_user, Permission.DELETE_COMMENT, comment.author_id):
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions to delete this comment"
        )

    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted successfully"}
