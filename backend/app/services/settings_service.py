import logging
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.models import SystemSetting, utc_now

logger = logging.getLogger("crafty_art_settings")

def get_system_setting(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve a setting value from the database, falling back to default."""
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting and setting.value is not None:
            return setting.value
    except Exception as e:
        logger.warning(f"Failed to read system setting '{key}': {str(e)}")
    return default

def set_system_setting(db: Session, key: str, value: Optional[str]) -> None:
    """Persist or update a system setting in the database."""
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not setting:
            setting = SystemSetting(key=key, value=value)
            db.add(setting)
        else:
            setting.value = value
            setting.updated_at = utc_now()
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save system setting '{key}': {str(e)}")
        raise
