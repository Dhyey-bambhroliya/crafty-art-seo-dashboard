import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings

logger = logging.getLogger("crafty_art_db")

def get_normalized_database_url(raw_url: str) -> str:
    """
    Normalizes PostgreSQL connection strings for SQLAlchemy 2.0 + Psycopg 3.
    Preserves SQLite URLs for local development and testing.
    """
    url = (raw_url or "").strip()
    if not url:
        return "sqlite:///./crafty_art_seo.db"

    # Convert standard postgres URIs to psycopg3 dialect
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql+psycopg://" + url[len("postgresql+psycopg2://"):]

    return url

normalized_database_url = get_normalized_database_url(settings.DATABASE_URL)

def get_masked_db_url(url: str = normalized_database_url) -> str:
    """Masks database password for safe logging and troubleshooting."""
    try:
        u = make_url(url)
        return u.render_as_string(hide_password=True)
    except Exception:
        # Fallback if URL parsing fails on abnormal characters
        return "<masked-database-url>"

engine_kwargs = {}
if normalized_database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Supabase PostgreSQL & Connection Pooler (PgBouncer/Supavisor) optimizations:
    # 1. Disable server-side prepared statement caching which poolers do not support
    engine_kwargs["connect_args"] = {
        "prepare_threshold": None,
    }
    # 2. Recycle connections to avoid stale/terminated pooled connections
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(
    normalized_database_url,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Create all tables if they don't exist yet with safe error reporting.
    Does NOT silently switch to SQLite if production PostgreSQL connection fails.
    """
    masked_url = get_masked_db_url()
    try:
        import backend.app.models  # ensures all models are imported
        logger.info(f"Connecting to database at: {masked_url}")
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        error_msg = (
            f"Failed to connect to database at '{masked_url}'. "
            f"Error details: {type(e).__name__}: {str(e)}. "
            "Please verify your DATABASE_URL in Render or .env. "
            "If your database password has special characters (such as '@', '#', or ':'), "
            "ensure they are URL-encoded (e.g. '@' as '%40'). "
            "Also ensure your Supabase project is active and that Session Pooler is used."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
