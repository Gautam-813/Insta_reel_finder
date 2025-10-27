"""Comment endpoints for reels."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import Comment, Reel, User
from backend.schemas import CommentCreate, CommentResponse, CommentListResponse, CommentUserInfo, MessageResponse

router = APIRouter(prefix="/api", tags=["comments"])


@router.get("/reels/{reel_id}/comments", response_model=CommentListResponse)
async def get_comments(
    reel_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get all comments for a specific reel."""
    # Check if reel exists
    reel = db.query(Reel).filter(Reel.id == reel_id).first()
    if not reel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reel not found"
        )

    # Get total count
    total = db.query(Comment).filter(Comment.reel_id == reel_id).count()

    # Fetch comments with pagination
    comments = (
        db.query(Comment)
        .filter(Comment.reel_id == reel_id)
        .order_by(Comment.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    # Build response with user info
    comment_responses = []
    for comment in comments:
        user_info = CommentUserInfo(
            id=comment.user.id,
            name=comment.user.name,
            profile_picture_url=comment.user.profile_picture_url
        )
        comment_response = CommentResponse(
            id=comment.id,
            comment_text=comment.comment_text,
            created_at=comment.created_at,
            user=user_info
        )
        comment_responses.append(comment_response)

    return CommentListResponse(comments=comment_responses, total=total)


@router.post("/reels/{reel_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    reel_id: str,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new comment on a reel. Requires authentication."""
    # Check if reel exists
    reel = db.query(Reel).filter(Reel.id == reel_id).first()
    if not reel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reel not found"
        )

    # Create comment
    new_comment = Comment(
        reel_id=reel.id,
        user_id=current_user.id,
        comment_text=comment_data.comment_text
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    # Build response
    user_info = CommentUserInfo(
        id=current_user.id,
        name=current_user.name,
        profile_picture_url=current_user.profile_picture_url
    )

    return CommentResponse(
        id=new_comment.id,
        comment_text=new_comment.comment_text,
        created_at=new_comment.created_at,
        user=user_info
    )


@router.delete("/comments/{comment_id}", response_model=MessageResponse)
async def delete_comment(
    comment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a comment. User can only delete their own comments."""
    # Find comment
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    # Check authorization - user can only delete their own comments
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments"
        )

    # Delete comment
    db.delete(comment)
    db.commit()

    return MessageResponse(message="Comment deleted successfully")
