from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from backend.database import Base


class User(Base):
    """User model for authenticated users."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    profile_picture_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    search_queries = relationship("SearchQuery", back_populates="user")


class OAuthAccount(Base):
    """OAuth account linkage for multiple providers per user."""
    __tablename__ = "oauth_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False)  # 'google' or 'github'
    provider_user_id = Column(String, nullable=False)  # OAuth provider's user ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="oauth_accounts")

    # Unique constraint on provider + provider_user_id
    __table_args__ = (
        Index('idx_provider_user', 'provider', 'provider_user_id', unique=True),
        Index('idx_user_id', 'user_id'),
    )


class Reel(Base):
    """Instagram reel data model."""
    __tablename__ = "reels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instagram_reel_id = Column(String, unique=True, nullable=False, index=True)
    reel_url = Column(String, nullable=False)
    thumbnail_url = Column(String)
    video_url = Column(String, nullable=True)
    caption = Column(Text, nullable=True)
    author_username = Column(String, nullable=False, index=True)
    like_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    instagram_comment_count = Column(Integer, default=0)
    post_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    search_caches = relationship("SearchCache", back_populates="reel", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="reel", cascade="all, delete-orphan")


class SearchCache(Base):
    """Cache table linking search queries to reels."""
    __tablename__ = "search_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(String, nullable=False)  # Lowercase search query
    reel_id = Column(UUID(as_uuid=True), ForeignKey("reels.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False)  # Position in search results (0-based)
    cached_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    reel = relationship("Reel", back_populates="search_caches")

    # Indexes for cache lookup
    __table_args__ = (
        Index('idx_query_cached_at', 'query', 'cached_at'),
        Index('idx_reel_id', 'reel_id'),
    )


class SearchQuery(Base):
    """Search analytics tracking."""
    __tablename__ = "search_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(String, nullable=False, index=True)  # Lowercase search query
    searched_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="search_queries")

    # Indexes
    __table_args__ = (
        Index('idx_query', 'query'),
        Index('idx_searched_at', 'searched_at'),
        Index('idx_user_id', 'user_id'),
    )


class Comment(Base):
    """User comments on reels."""
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reel_id = Column(UUID(as_uuid=True), ForeignKey("reels.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    reel = relationship("Reel", back_populates="comments")
    user = relationship("User", back_populates="comments")

    # Indexes
    __table_args__ = (
        Index('idx_reel_id', 'reel_id'),
        Index('idx_user_id', 'user_id'),
    )
