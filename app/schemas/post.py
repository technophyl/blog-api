from pydantic import ConfigDict, BaseModel, field_validator
from typing import List, Optional
from datetime import datetime


class TagBase(BaseModel):
    name: str


class Tag(TagBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class PostBase(BaseModel):
    title: str
    content: str
    tags: List[str] = []


class PostCreate(PostBase):
    title: str
    content: str
    tags: List[str] = []

    @field_validator('title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Title must not be empty')
        return v

    @field_validator('content')
    def content_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Content must not be empty')
        return v


class PostUpdate(PostBase):
    pass


class Post(PostBase):
    id: int
    created_at: datetime
    updated_at: datetime
    author_id: int
    tags: List[Tag] = []
    model_config = ConfigDict(from_attributes=True)


class PostFilter(BaseModel):
    keyword: Optional[str] = None
    author_id: Optional[int] = None
    tag: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
