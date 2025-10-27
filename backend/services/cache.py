"""Cache management for search results."""

from sqlalchemy.orm import Session
from sqlalchemy import and_, delete
from datetime import datetime, timedelta
from typing import List, Optional
from backend.models import SearchCache, Reel
from backend.config import settings


def check_cache(db: Session, query: str) -> Optional[List[Reel]]:
    """
    Check if search results are cached and still valid.

    Args:
        db: Database session
        query: Normalized search query (lowercase)

    Returns:
        List of Reel objects if cache is valid, None otherwise
    """
    # Calculate cache expiry time
    cache_cutoff = datetime.utcnow() - timedelta(hours=settings.CACHE_EXPIRY_HOURS)

    # Query cache entries for this query within the cache window
    cache_entries = (
        db.query(SearchCache)
        .filter(
            and_(
                SearchCache.query == query,
                SearchCache.cached_at >= cache_cutoff
            )
        )
        .order_by(SearchCache.position)
        .all()
    )

    if not cache_entries:
        return None

    # Extract reels from cache entries
    reels = [entry.reel for entry in cache_entries if entry.reel]

    return reels if reels else None


def update_cache(db: Session, query: str, reels: List[Reel]) -> None:
    """
    Update cache with new search results.
    Deletes old cache entries for this query and creates new ones.

    Args:
        db: Database session
        query: Normalized search query (lowercase)
        reels: List of Reel objects to cache
    """
    # Delete old cache entries for this query
    db.execute(
        delete(SearchCache).where(SearchCache.query == query)
    )
    db.commit()

    # Create new cache entries
    for position, reel in enumerate(reels):
        cache_entry = SearchCache(
            query=query,
            reel_id=reel.id,
            position=position,
            cached_at=datetime.utcnow()
        )
        db.add(cache_entry)

    db.commit()


def clear_expired_cache(db: Session) -> int:
    """
    Clear all expired cache entries from the database.
    This can be called periodically to clean up old data.

    Args:
        db: Database session

    Returns:
        Number of cache entries deleted
    """
    cache_cutoff = datetime.utcnow() - timedelta(hours=settings.CACHE_EXPIRY_HOURS)

    result = db.execute(
        delete(SearchCache).where(SearchCache.cached_at < cache_cutoff)
    )
    db.commit()

    return result.rowcount if result.rowcount else 0
