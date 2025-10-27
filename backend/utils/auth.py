from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from backend.config import settings


def create_access_token(user_id: UUID) -> str:
    """
    Generate a JWT access token for a user.

    Args:
        user_id: The user's UUID

    Returns:
        Encoded JWT token string
    """
    # Token expires in 7 days
    expire = datetime.utcnow() + timedelta(days=7)

    # Create JWT payload
    payload = {
        "sub": str(user_id),  # Subject (user ID)
        "exp": expire  # Expiration time
    }

    # Encode and sign the token
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


def verify_access_token(token: str) -> Optional[UUID]:
    """
    Verify and decode a JWT access token.

    Args:
        token: The JWT token string

    Returns:
        User UUID if token is valid, None otherwise

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        # Decode and verify the token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

        # Extract user ID from subject claim
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise JWTError("Token missing subject claim")

        # Convert string to UUID
        user_id = UUID(user_id_str)
        return user_id

    except JWTError:
        raise
    except (ValueError, TypeError) as e:
        raise JWTError(f"Invalid user ID in token: {e}")
