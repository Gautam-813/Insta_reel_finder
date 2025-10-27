from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# User schemas
class UserBase(BaseModel):
    """Base user schema."""
    email: str
    name: str
    profile_picture_url: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user."""
    pass


class UserResponse(UserBase):
    """Schema for user responses."""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class UserWithProvider(UserResponse):
    """User response with OAuth provider info (for /api/auth/me)."""
    oauth_provider: str  # Will be populated from the most recent oauth_account

    class Config:
        from_attributes = True


# Reel schemas
class ReelBase(BaseModel):
    """Base reel schema."""
    instagram_reel_id: str
    reel_url: str
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    caption: Optional[str] = None
    author_username: str
    like_count: int = 0
    view_count: int = 0
    instagram_comment_count: int = 0
    post_date: Optional[datetime] = None


class ReelCreate(ReelBase):
    """Schema for creating a reel."""
    pass


class ReelResponse(ReelBase):
    """Schema for reel responses."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReelWithCommentCount(ReelResponse):
    """Reel response with app comment count."""
    app_comment_count: int = 0


# Comment schemas
class CommentBase(BaseModel):
    """Base comment schema."""
    comment_text: str = Field(..., min_length=1, max_length=1000)

    @validator('comment_text')
    def validate_comment_text(cls, v):
        """Trim whitespace and validate not empty."""
        v = v.strip()
        if not v:
            raise ValueError('Comment cannot be empty')
        return v


class CommentCreate(CommentBase):
    """Schema for creating a comment."""
    pass


class CommentUserInfo(BaseModel):
    """User info embedded in comment response."""
    id: UUID
    name: str
    profile_picture_url: Optional[str] = None

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    """Schema for comment responses."""
    id: UUID
    comment_text: str
    created_at: datetime
    user: CommentUserInfo

    class Config:
        from_attributes = True


class CommentListResponse(BaseModel):
    """Schema for listing comments."""
    comments: List[CommentResponse]
    total: int


# Search schemas
class SearchResultResponse(BaseModel):
    """Schema for search results."""
    query: str
    cached: bool
    results: List[ReelWithCommentCount]


class TrendingQuery(BaseModel):
    """Schema for a trending query."""
    query: str
    count: int


class TrendingQueriesResponse(BaseModel):
    """Schema for trending queries response."""
    trending: List[TrendingQuery]


# Authentication schemas
class LoginResponse(BaseModel):
    """Schema for login response."""
    message: str
    user: UserResponse


class LogoutResponse(BaseModel):
    """Schema for logout response."""
    message: str


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
