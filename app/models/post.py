from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

post_tags = Table('post_tags', Base.metadata,
                  Column('post_id', Integer, ForeignKey('posts.id')),
                  Column('tag_id', Integer, ForeignKey('tags.id'))
                  )


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    author_id = Column(Integer, ForeignKey("users.id"))

    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post")
    tags = relationship("Tag", secondary=post_tags, back_populates="posts")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    posts = relationship("Post", secondary=post_tags, back_populates="tags")
