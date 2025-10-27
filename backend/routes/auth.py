"""Authentication endpoints for OAuth (Google and GitHub)."""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import User, OAuthAccount
from backend.schemas import UserWithProvider, LogoutResponse
from backend.services.oauth import exchange_google_code, exchange_github_code, create_or_update_user
from backend.utils.auth import create_access_token
from backend.config import settings
import httpx

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.get("/login/google")
async def login_google():
    """Initiate Google OAuth login flow."""
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile"
    )
    return RedirectResponse(url=google_auth_url)


@router.get("/callback/google")
async def callback_google(
    code: str,
    response: Response,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback."""
    if not code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization code missing"
        )

    try:
        # Exchange code for user info
        oauth_data = await exchange_google_code(code)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google OAuth failed: {str(e)}"
        )

    # Create or update user
    user = create_or_update_user(db, oauth_data)

    # Generate JWT token
    access_token = create_access_token(user.id)

    # Set HTTP-only cookie
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=7 * 24 * 60 * 60  # 7 days
    )

    return response


@router.get("/login/github")
async def login_github():
    """Initiate GitHub OAuth login flow."""
    github_auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={settings.GITHUB_CLIENT_ID}&"
        f"redirect_uri={settings.GITHUB_REDIRECT_URI}&"
        f"scope=user:email"
    )
    return RedirectResponse(url=github_auth_url)


@router.get("/callback/github")
async def callback_github(
    code: str,
    response: Response,
    db: Session = Depends(get_db)
):
    """Handle GitHub OAuth callback."""
    if not code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization code missing"
        )

    try:
        # Exchange code for user info
        oauth_data = await exchange_github_code(code)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub OAuth failed: {str(e)}"
        )

    # Create or update user
    user = create_or_update_user(db, oauth_data)

    # Generate JWT token
    access_token = create_access_token(user.id)

    # Set HTTP-only cookie
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=7 * 24 * 60 * 60  # 7 days
    )

    return response


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response):
    """Log out the current user by clearing the session cookie."""
    response.delete_cookie(key="access_token")
    return LogoutResponse(message="Logged out successfully")


@router.get("/me", response_model=UserWithProvider)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current authenticated user information."""
    # Get the most recent OAuth provider for this user
    oauth_account = (
        db.query(OAuthAccount)
        .filter(OAuthAccount.user_id == current_user.id)
        .order_by(OAuthAccount.created_at.desc())
        .first()
    )

    oauth_provider = oauth_account.provider if oauth_account else "unknown"

    return UserWithProvider(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        profile_picture_url=current_user.profile_picture_url,
        created_at=current_user.created_at,
        oauth_provider=oauth_provider
    )
