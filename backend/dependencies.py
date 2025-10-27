from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy.orm import Session
from typing import Optional
from jose import JWTError
from backend.database import get_db
from backend.utils.auth import verify_access_token
from backend.models import User


async def get_current_user(
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    Args:
        access_token: JWT token from HTTP-only cookie
        db: Database session

    Returns:
        User model instance

    Raises:
        HTTPException: 401 if not authenticated or token invalid
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        # Verify and decode the token
        user_id = verify_access_token(access_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


async def get_optional_user(
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    FastAPI dependency to optionally get the current authenticated user.
    Returns None if not authenticated instead of raising an exception.

    Args:
        access_token: JWT token from HTTP-only cookie
        db: Database session

    Returns:
        User model instance if authenticated, None otherwise
    """
    if not access_token:
        return None

    try:
        # Verify and decode the token
        user_id = verify_access_token(access_token)

        # Fetch user from database
        user = db.query(User).filter(User.id == user_id).first()
        return user
    except (JWTError, Exception):
        return None
