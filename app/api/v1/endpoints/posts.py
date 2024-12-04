from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.api import deps
from app.core.permissions import Permission, require_permission
from app.core.cache import cached
from app.schemas.user import User
from app.schemas.post import Post, PostCreate, PostUpdate, PostFilter
from app.models.post import Post as PostModel, Tag as TagModel


router = APIRouter()


@router.post("/", response_model=Post)
@require_permission(Permission.CREATE_POST)
async def create_post(
    *,
    post_in: PostCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Post:
    """Create a new blog post."""
    # Process tags
    tags = []
    for tag_name in post_in.tags:
        tag = db.query(TagModel).filter(TagModel.name == tag_name).first()
        if not tag:
            tag = TagModel(name=tag_name)
            db.add(tag)
        tags.append(tag)

    post = PostModel(
        title=post_in.title,
        content=post_in.content,
        author_id=current_user.id,
        tags=tags
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/{post_id}", response_model=Post)
@cached(expire=300, namespace="post_detail")  # Cache for 5 minutes
async def get_post(
    post_id: int,
    db: Session = Depends(deps.get_db)
) -> Post:
    """Get a specific post by ID."""
    post = db.query(PostModel).filter(PostModel.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.get("/", response_model=List[Post])
@cached(expire=60, namespace="post_list")  # Cache for 1 minute
def get_posts(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 10,
    filter_params: PostFilter = Depends()
) -> List[Post]:
    """Get all posts with optional filtering."""
    query = db.query(PostModel)

    if filter_params.keyword:
        query = query.filter(
            (PostModel.title.ilike(f"%{filter_params.keyword}%")) |
            (PostModel.content.ilike(f"%{filter_params.keyword}%"))
        )

    if filter_params.author_id:
        query = query.filter(PostModel.author_id == filter_params.author_id)

    if filter_params.tag:
        query = query.filter(PostModel.tags.any(
            TagModel.name == filter_params.tag))

    if filter_params.start_date:
        query = query.filter(PostModel.created_at >= filter_params.start_date)

    if filter_params.end_date:
        query = query.filter(PostModel.created_at <= filter_params.end_date)

    return query.offset(skip).limit(limit).all()


@router.put("/{post_id}", response_model=Post)
@require_permission(Permission.EDIT_POST)
async def update_post(
    *,
    db: Session = Depends(deps.get_db),
    post_id: int,
    post_in: PostUpdate,
    current_user: User = Depends(deps.get_current_user)
) -> Post:
    """Update a blog post."""
    post = db.query(PostModel).filter(PostModel.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Update tags if provided
    if post_in.tags is not None:
        tags = []
        for tag_name in post_in.tags:
            tag = db.query(TagModel).filter(TagModel.name == tag_name).first()
            if not tag:
                tag = TagModel(name=tag_name)
                db.add(tag)
            tags.append(tag)
        post.tags = tags

    # Update other fields
    for field, value in post_in.model_dump(exclude={'tags'}).items():
        if value is not None:
            setattr(post, field, value)

    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}")
@require_permission(Permission.DELETE_POST)
async def delete_post(
    *,
    db: Session = Depends(deps.get_db),
    post_id: int,
    current_user: User = Depends(deps.get_current_user)
) -> dict:
    """Delete a blog post."""
    post = db.query(PostModel).filter(PostModel.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    db.delete(post)
    db.commit()
    return {"message": "Post deleted successfully"}
