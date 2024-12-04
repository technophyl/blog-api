from pydantic import ConfigDict, BaseModel, field_validator
from datetime import datetime


class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    post_id: int
    content: str

    @field_validator('content')
    def content_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Content must not be empty')
        return v


class CommentUpdate(CommentBase):
    pass


class Comment(CommentBase):
    id: int
    post_id: int
    author_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
