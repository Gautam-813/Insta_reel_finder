"""Input validation utilities."""


def validate_search_query(query: str) -> str:
    """
    Validate and normalize a search query.

    Args:
        query: The search query string

    Returns:
        Normalized query (lowercase, stripped)

    Raises:
        ValueError: If query is invalid
    """
    if not query:
        raise ValueError("Search query cannot be empty")

    # Normalize: lowercase and strip whitespace
    normalized = query.lower().strip()

    if not normalized:
        raise ValueError("Search query cannot be empty")

    if len(normalized) > 200:
        raise ValueError("Search query too long (maximum 200 characters)")

    return normalized


def sanitize_string(text: str) -> str:
    """
    Sanitize a string by removing potentially dangerous characters.

    Args:
        text: Input string

    Returns:
        Sanitized string
    """
    # Remove null bytes and other control characters
    sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    return sanitized.strip()
