"""Search and reel endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime, timedelta
from backend.database import get_db
from backend.dependencies import get_optional_user
from backend.models import Reel, SearchQuery, Comment, User
from backend.schemas import SearchResultResponse, ReelResponse, ReelWithCommentCount, TrendingQueriesResponse, TrendingQuery
from backend.services.scraper import get_scraper
from backend.services.cache import check_cache, update_cache
from backend.utils.validators import validate_search_query
from backend.config import settings

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResultResponse)
async def search_reels(
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Search for Instagram reels by keyword.
    Uses cache if available (24 hours), otherwise scrapes Instagram.
    """
    try:
        # Validate and normalize query
        normalized_query = validate_search_query(query)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Log search query for analytics
    search_log = SearchQuery(
        query=normalized_query,
        user_id=current_user.id if current_user else None
    )
    db.add(search_log)
    db.commit()

    # Check cache first
    cached_reels = check_cache(db, normalized_query)

    if cached_reels:
        # Return cached results
        reels_with_counts = []
        for reel in cached_reels:
            comment_count = db.query(Comment).filter(Comment.reel_id == reel.id).count()
            reel_dict = {
                "id": reel.id,
                "instagram_reel_id": reel.instagram_reel_id,
                "reel_url": reel.reel_url,
                "thumbnail_url": reel.thumbnail_url,
                "video_url": reel.video_url,
                "caption": reel.caption,
                "author_username": reel.author_username,
                "like_count": reel.like_count,
                "view_count": reel.view_count,
                "instagram_comment_count": reel.instagram_comment_count,
                "post_date": reel.post_date,
                "created_at": reel.created_at,
                "updated_at": reel.updated_at,
                "app_comment_count": comment_count
            }
            reels_with_counts.append(ReelWithCommentCount(**reel_dict))

        return SearchResultResponse(
            query=normalized_query,
            cached=True,
            results=reels_with_counts
        )

    # Cache miss - scrape Instagram
    try:
        scraper = get_scraper()
        scraped_data = scraper.scrape_reels(normalized_query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape Instagram: {str(e)}"
        )

    if not scraped_data:
        # No results found
        return SearchResultResponse(
            query=normalized_query,
            cached=False,
            results=[]
        )

    # Store/update reels in database
    reels = []
    for data in scraped_data:
        # Check if reel already exists
        existing_reel = db.query(Reel).filter(
            Reel.instagram_reel_id == data["instagram_reel_id"]
        ).first()

        if existing_reel:
            # Update existing reel data
            existing_reel.thumbnail_url = data.get("thumbnail_url") or existing_reel.thumbnail_url
            existing_reel.video_url = data.get("video_url") or existing_reel.video_url
            existing_reel.caption = data.get("caption") or existing_reel.caption
            existing_reel.author_username = data.get("author_username", existing_reel.author_username)
            existing_reel.like_count = data.get("like_count", existing_reel.like_count)
            existing_reel.view_count = data.get("view_count", existing_reel.view_count)
            existing_reel.instagram_comment_count = data.get("instagram_comment_count", existing_reel.instagram_comment_count)
            existing_reel.updated_at = datetime.utcnow()
            reels.append(existing_reel)
        else:
            # Create new reel
            new_reel = Reel(
                instagram_reel_id=data["instagram_reel_id"],
                reel_url=data["reel_url"],
                thumbnail_url=data.get("thumbnail_url"),
                video_url=data.get("video_url"),
                caption=data.get("caption"),
                author_username=data.get("author_username", "unknown"),
                like_count=data.get("like_count", 0),
                view_count=data.get("view_count", 0),
                instagram_comment_count=data.get("instagram_comment_count", 0),
                post_date=data.get("post_date")
            )
            db.add(new_reel)
            reels.append(new_reel)

    db.commit()

    # Refresh reels to get IDs
    for reel in reels:
        db.refresh(reel)

    # Update cache
    update_cache(db, normalized_query, reels)

    # Prepare response with comment counts
    reels_with_counts = []
    for reel in reels:
        comment_count = db.query(Comment).filter(Comment.reel_id == reel.id).count()
        reel_dict = {
            "id": reel.id,
            "instagram_reel_id": reel.instagram_reel_id,
            "reel_url": reel.reel_url,
            "thumbnail_url": reel.thumbnail_url,
            "video_url": reel.video_url,
            "caption": reel.caption,
            "author_username": reel.author_username,
            "like_count": reel.like_count,
            "view_count": reel.view_count,
            "instagram_comment_count": reel.instagram_comment_count,
            "post_date": reel.post_date,
            "created_at": reel.created_at,
            "updated_at": reel.updated_at,
            "app_comment_count": comment_count
        }
        reels_with_counts.append(ReelWithCommentCount(**reel_dict))

    return SearchResultResponse(
        query=normalized_query,
        cached=False,
        results=reels_with_counts
    )


@router.get("/reels/{reel_id}", response_model=ReelResponse)
async def get_reel(
    reel_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific reel."""
    reel = db.query(Reel).filter(Reel.id == reel_id).first()

    if not reel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reel not found"
        )

    return reel


@router.get("/trending", response_model=TrendingQueriesResponse)
async def get_trending_searches(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get trending search queries from the last 24 hours."""
    # Calculate 24 hours ago
    cutoff_time = datetime.utcnow() - timedelta(hours=24)

    # Query trending searches
    trending = (
        db.query(
            SearchQuery.query,
            func.count(SearchQuery.id).label("count")
        )
        .filter(SearchQuery.searched_at >= cutoff_time)
        .group_by(SearchQuery.query)
        .order_by(desc("count"))
        .limit(limit)
        .all()
    )

    trending_list = [
        TrendingQuery(query=item.query, count=item.count)
        for item in trending
    ]

    return TrendingQueriesResponse(trending=trending_list)
