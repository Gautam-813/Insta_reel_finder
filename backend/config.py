from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # GitHub OAuth
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_REDIRECT_URI: str

    # Application
    CACHE_EXPIRY_HOURS: int = 24
    MAX_SEARCH_RESULTS: int = 20

    # Selenium (optional)
    SELENIUM_DRIVER_PATH: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
