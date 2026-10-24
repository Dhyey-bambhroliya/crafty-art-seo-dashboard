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
    
    # CORS & Frontend Origins
    FRONTEND_URL: Optional[str] = "https://crafty-art-seo-dashboard.vercel.app"
    ADDITIONAL_CORS_ORIGINS: Optional[str] = None
    CORS_ORIGIN_REGEX: Optional[str] = r"^https:\/\/.*\.vercel\.app$"
    
    # Google OAuth & Search Console
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "https://crafty-art-seo-dashboard.vercel.app/gsc-connection"
    GSC_READONLY_SCOPE: str = "https://www.googleapis.com/auth/webmasters.readonly"
    
    # Sync & Schedule
    ENABLE_SCHEDULER: bool = True
    DAILY_SYNC_HOUR: int = 3  # 03:00 AM UTC
    DEFAULT_GSC_PROPERTY: Optional[str] = None
    
    # Thresholds defaults
    DEFAULT_CLICK_WARNING_PCT: float = 10.0
    DEFAULT_CLICK_CRITICAL_PCT: float = 20.0
    DEFAULT_IMPRESSION_WARNING_PCT: float = 20.0
    DEFAULT_POSITION_DROP_WARNING: float = 3.0
    DEFAULT_MIN_PREVIOUS_CLICKS: int = 5
    DEFAULT_MIN_PREVIOUS_IMPRESSIONS: int = 25

    @property
    def cors_origins(self) -> List[str]:
        base_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "https://crafty-art-seo-dashboard.vercel.app",
            "https://crafty-art-seo-dashboard-e5q96gbo8-new-journy.vercel.app",
        ]
        if self.FRONTEND_URL:
            for item in self.FRONTEND_URL.split(","):
                clean = item.strip().rstrip("/")
                if clean and clean not in base_origins:
                    base_origins.append(clean)
        if self.ADDITIONAL_CORS_ORIGINS:
            for item in self.ADDITIONAL_CORS_ORIGINS.split(","):
                clean_item = item.strip().rstrip("/")
                if clean_item and clean_item not in base_origins:
                    base_origins.append(clean_item)
        return base_origins

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
