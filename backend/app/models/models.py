from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Float, Text,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class UserRole:
    MANAGER = "MANAGER"
    TEAM_LEADER = "TEAM_LEADER"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.TEAM_LEADER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    categories = relationship("Category", back_populates="leader")
    reviewed_alerts = relationship("Alert", back_populates="reviewed_by_user", foreign_keys="Alert.reviewed_by_user_id")

class GSCProperty(Base):
    __tablename__ = "gsc_properties"

    id = Column(Integer, primary_key=True, index=True)
    site_url = Column(String(500), unique=True, index=True, nullable=False)
    permission_level = Column(String(100), default="siteRestrictedUser", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Secure server-side OAuth credentials (never exposed via API)
    client_id = Column(String(255), nullable=True)
    client_secret = Column(String(255), nullable=True)
    refresh_token = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    
    connected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    sync_runs = relationship("SyncRun", back_populates="property")
    metrics = relationship("DailyPageMetrics", back_populates="property")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    assigned_leader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, INACTIVE, ARCHIVED
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    leader = relationship("User", back_populates="categories")
    pages = relationship("CategoryPage", back_populates="category", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="category")

class CategoryPage(Base):
    __tablename__ = "category_pages"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    full_url = Column(String(1000), index=True, nullable=False)
    normalized_url = Column(String(1000), index=True, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, PAUSED, REMOVED
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    category = relationship("Category", back_populates="pages")

    __table_args__ = (
        Index("idx_category_normalized_url", "category_id", "normalized_url"),
    )

class DailyPageMetrics(Base):
    __tablename__ = "daily_page_metrics"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("gsc_properties.id"), nullable=True, index=True)
    page_url = Column(String(1000), index=True, nullable=False)
    normalized_url = Column(String(1000), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    clicks = Column(Integer, default=0, nullable=False)
    impressions = Column(Integer, default=0, nullable=False)
    ctr = Column(Float, default=0.0, nullable=False)
    position = Column(Float, default=0.0, nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False)

    property = relationship("GSCProperty", back_populates="metrics")

    __table_args__ = (
        UniqueConstraint("property_id", "normalized_url", "date", name="uq_property_page_date"),
        Index("idx_metrics_date_normurl", "date", "normalized_url"),
    )

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    page_url = Column(String(1000), index=True, nullable=False)
    normalized_url = Column(String(1000), index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_leader_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    alert_type = Column(String(100), nullable=False)  # CLICK_DECLINE_WARNING, CLICK_DECLINE_CRITICAL, IMPRESSION_DECLINE_WARNING, POSITION_DROP_WARNING
    severity = Column(String(50), nullable=False)    # WARNING, CRITICAL
    current_value = Column(Float, nullable=False)
    previous_value = Column(Float, nullable=False)
    pct_change = Column(Float, nullable=False)
    detection_date = Column(Date, nullable=False)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, REVIEWED, DISMISSED
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    category = relationship("Category", back_populates="alerts")
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by_user_id], back_populates="reviewed_alerts")

    __table_args__ = (
        Index("idx_alert_unique_check", "normalized_url", "alert_type", "detection_date"),
    )

class SyncRun(Base):
    __tablename__ = "sync_runs"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("gsc_properties.id"), nullable=True, index=True)
    triggered_by = Column(String(100), default="SYSTEM", nullable=False)  # SYSTEM, SCHEDULED, USER:<id>
    start_time = Column(DateTime, default=utc_now, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(50), default="RUNNING", nullable=False)  # RUNNING, SUCCESS, FAILED, PARTIAL
    pages_synced = Column(Integer, default=0, nullable=False)
    records_created = Column(Integer, default=0, nullable=False)
    alerts_generated = Column(Integer, default=0, nullable=False)
    latest_data_date = Column(Date, nullable=True)
    error_message = Column(Text, nullable=True)

    property = relationship("GSCProperty", back_populates="sync_runs")

class AlertSetting(Base):
    __tablename__ = "alert_settings"

    id = Column(Integer, primary_key=True, index=True)
    click_warning_pct = Column(Float, default=10.0, nullable=False)
    click_critical_pct = Column(Float, default=20.0, nullable=False)
    impression_warning_pct = Column(Float, default=20.0, nullable=False)
    position_drop_warning = Column(Float, default=3.0, nullable=False)
    min_previous_clicks = Column(Integer, default=5, nullable=False)
    min_previous_impressions = Column(Integer, default=25, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
