from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id:            Mapped[int]       = mapped_column(primary_key=True)
    username:      Mapped[str]       = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str]       = mapped_column(String(255))
    bio:           Mapped[str | None] = mapped_column(String(200), default=None)
    created_at:    Mapped[datetime]  = mapped_column(DateTime, server_default=func.now())

    posts: Mapped[list["Post"]] = relationship(back_populates="author", cascade="all, delete-orphan")


class Post(Base):
    __tablename__ = "posts"

    id:         Mapped[int]      = mapped_column(primary_key=True)
    author_id:  Mapped[int]      = mapped_column(ForeignKey("users.id"), index=True)
    body:       Mapped[str]      = mapped_column(String(280))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    author: Mapped["User"]        = relationship(back_populates="posts")
    likes:  Mapped[list["Like"]]  = relationship(back_populates="post", cascade="all, delete-orphan")


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "post_id"),)

    id:      Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)

    post: Mapped["Post"] = relationship(back_populates="likes")


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "followee_id"),)

    id:          Mapped[int]      = mapped_column(primary_key=True)
    follower_id: Mapped[int]      = mapped_column(ForeignKey("users.id"), index=True)
    followee_id: Mapped[int]      = mapped_column(ForeignKey("users.id"), index=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
