from fastapi import APIRouter
from app.api.v1.endpoints import auth, posts, comments

api_router = APIRouter()

# Include all routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

api_router.include_router(
    posts.router,
    prefix="/posts",
    tags=["posts"]
)

api_router.include_router(
    comments.router,
    prefix="/comments",
    tags=["comments"]
)
