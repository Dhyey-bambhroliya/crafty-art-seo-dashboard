from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import secrets

class Settings(BaseSettings):
    PROJECT_NAME: str = "Crafty Art SEO Management Dashboard"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = "sqlite:///./crafty_art_seo.db"
    
    # Security
    SECRET_KEY: str = "craftyart-production-ready-super-secret-key-seo-dashboard-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Google OAuth & Search Console
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/gsc-callback"
    GSC_READONLY_SCOPE: str = "https://www.googleapis.com/auth/webmasters.readonly"
    
    # Sync & Schedule
    DAILY_SYNC_HOUR: int = 3  # 03:00 AM
    DEFAULT_GSC_PROPERTY: Optional[str] = None
    
    # Thresholds defaults
    DEFAULT_CLICK_WARNING_PCT: float = 10.0
    DEFAULT_CLICK_CRITICAL_PCT: float = 20.0
    DEFAULT_IMPRESSION_WARNING_PCT: float = 20.0
    DEFAULT_POSITION_DROP_WARNING: float = 3.0
    DEFAULT_MIN_PREVIOUS_CLICKS: int = 5
    DEFAULT_MIN_PREVIOUS_IMPRESSIONS: int = 25
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
