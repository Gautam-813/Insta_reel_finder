"""OAuth service for Google and GitHub authentication."""

import httpx
from sqlalchemy.orm import Session
from typing import Dict, Optional
from backend.config import settings
from backend.models import User, OAuthAccount


async def exchange_google_code(code: str) -> Dict:
    """
    Exchange Google OAuth authorization code for access token and user info.

    Args:
        code: Authorization code from Google

    Returns:
        Dictionary with user data

    Raises:
        httpx.HTTPError: If OAuth exchange fails
    """
    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )
        token_response.raise_for_status()
        tokens = token_response.json()

        # Fetch user info from Google
        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        user_info_response.raise_for_status()
        user_info = user_info_response.json()

        return {
            "provider": "google",
            "provider_user_id": user_info["id"],
            "email": user_info["email"],
            "name": user_info.get("name", user_info["email"].split("@")[0]),
            "profile_picture_url": user_info.get("picture")
        }


async def exchange_github_code(code: str) -> Dict:
    """
    Exchange GitHub OAuth authorization code for access token and user info.

    Args:
        code: Authorization code from GitHub

    Returns:
        Dictionary with user data

    Raises:
        httpx.HTTPError: If OAuth exchange fails
    """
    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "code": code,
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "redirect_uri": settings.GITHUB_REDIRECT_URI
            },
            headers={"Accept": "application/json"}
        )
        token_response.raise_for_status()
        tokens = token_response.json()

        if "error" in tokens:
            raise httpx.HTTPError(f"GitHub OAuth error: {tokens.get('error_description', 'Unknown error')}")

        # Fetch user info from GitHub
        user_info_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {tokens['access_token']}",
                "Accept": "application/json"
            }
        )
        user_info_response.raise_for_status()
        user_info = user_info_response.json()

        # Fetch user email (may be in separate endpoint)
        email = user_info.get("email")
        if not email:
            email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {tokens['access_token']}",
                    "Accept": "application/json"
                }
            )
            if email_response.status_code == 200:
                emails = email_response.json()
                primary_email = next((e for e in emails if e.get("primary")), None)
                if primary_email:
                    email = primary_email["email"]

        if not email:
            raise httpx.HTTPError("Email permission required")

        return {
            "provider": "github",
            "provider_user_id": str(user_info["id"]),
            "email": email,
            "name": user_info.get("name") or user_info.get("login", email.split("@")[0]),
            "profile_picture_url": user_info.get("avatar_url")
        }


def create_or_update_user(db: Session, oauth_data: Dict) -> User:
    """
    Create or update a user based on OAuth data.
    Follows the updated schema with oauth_accounts table.

    Args:
        db: Database session
        oauth_data: Dictionary with OAuth user data

    Returns:
        User model instance
    """
    provider = oauth_data["provider"]
    provider_user_id = oauth_data["provider_user_id"]
    email = oauth_data["email"]
    name = oauth_data["name"]
    profile_picture_url = oauth_data.get("profile_picture_url")

    # Check if OAuth account already exists
    oauth_account = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id
        )
        .first()
    )

    if oauth_account:
        # Existing OAuth account - get the user and update info
        user = oauth_account.user

        # Update user info if changed
        if user.email != email:
            user.email = email
        if user.name != name:
            user.name = name
        if profile_picture_url and user.profile_picture_url != profile_picture_url:
            user.profile_picture_url = profile_picture_url

        db.commit()
        db.refresh(user)
        return user

    # No existing OAuth account - check if user with email exists
    user = db.query(User).filter(User.email == email).first()

    if user:
        # User exists with this email - link new OAuth provider
        new_oauth_account = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id
        )
        db.add(new_oauth_account)

        # Update user info if needed
        if profile_picture_url and not user.profile_picture_url:
            user.profile_picture_url = profile_picture_url

        db.commit()
        db.refresh(user)
        return user

    # No existing user - create new user and OAuth account
    new_user = User(
        email=email,
        name=name,
        profile_picture_url=profile_picture_url
    )
    db.add(new_user)
    db.flush()  # Get the user ID

    new_oauth_account = OAuthAccount(
        user_id=new_user.id,
        provider=provider,
        provider_user_id=provider_user_id
    )
    db.add(new_oauth_account)
    db.commit()
    db.refresh(new_user)

    return new_user
