from datetime import datetime, timezone, date
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Float, Text,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.models import utc_now

class FestivalTaskStatus:
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    COMPLETED = "COMPLETED"

class FestivalNotificationType:
    FESTIVAL_30_DAY_REMINDER = "FESTIVAL_30_DAY_REMINDER"
    FESTIVAL_15_DAY_REMINDER = "FESTIVAL_15_DAY_REMINDER"
    FESTIVAL_7_DAY_REMINDER = "FESTIVAL_7_DAY_REMINDER"
    FESTIVAL_TASK_OVERDUE = "FESTIVAL_TASK_OVERDUE"
    FESTIVAL_PERFORMANCE_DECLINE = "FESTIVAL_PERFORMANCE_DECLINE"
    FESTIVAL_DATE_APPROVAL = "FESTIVAL_DATE_APPROVAL"

class FestivalDateStatus:
    UNVERIFIED = "UNVERIFIED"
    ESTIMATED = "ESTIMATED"
    CONFIRMED = "CONFIRMED"

class FestivalApprovalStatus:
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class Festival(Base):
    """
    Core Festival entity representing a recurring festival campaign (e.g. Diwali, Holi, Christmas, Halloween).
    Encapsulates country, regional focus, and assigned team leader.
    Year-specific calendar dates are decoupled into FestivalYearDate to seamlessly support
    comparing different years (e.g., Diwali 2025 vs Diwali 2026).
    """
    __tablename__ = "festivals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    country_code = Column(String(10), default="IN", index=True, nullable=False)  # IN, US, UK, CA, AU, GLOBAL
    region = Column(String(255), nullable=True)  # Optional regional distinction (e.g. Gujarat, Scotland)
    category_group = Column(String(100), default="Cultural", nullable=False)  # Cultural, Religious, Commercial, National
    description = Column(Text, nullable=True)
    assigned_leader_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    assigned_leader = relationship("User", foreign_keys=[assigned_leader_id])
    year_dates = relationship("FestivalYearDate", back_populates="festival", cascade="all, delete-orphan", order_by="FestivalYearDate.year.desc()")
    subcategories = relationship("FestivalSubcategory", back_populates="festival", cascade="all, delete-orphan", order_by="FestivalSubcategory.name")
    pages = relationship("FestivalPage", back_populates="festival", cascade="all, delete-orphan")
    tasks = relationship("FestivalTask", back_populates="festival", cascade="all, delete-orphan")
    notifications = relationship("FestivalNotification", back_populates="festival", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_festival_country_active", "country_code", "is_active"),
    )

class FestivalYearDate(Base):
    """
    Year-specific edition of a festival with precise lunar/solar calendar dates.
    Enables comparing campaigns year-over-year (e.g. Diwali 2024 vs 2025 vs 2026).
    Stores SEO preparation milestones (prep start date, deadline) and manager date approval.
    """
    __tablename__ = "festival_year_dates"

    id = Column(Integer, primary_key=True, index=True)
    festival_id = Column(Integer, ForeignKey("festivals.id", ondelete="CASCADE"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    prep_start_date = Column(Date, nullable=True)  # Kickoff date for SEO updates (typically 30-60 days prior)
    prep_deadline_date = Column(Date, nullable=True)  # Final readiness deadline (typically 7-15 days prior)
    season_comparison_start = Column(Date, nullable=True)  # GSC analytics window start date for this year's edition
    season_comparison_end = Column(Date, nullable=True)  # GSC analytics window end date for this year's edition
    date_status = Column(String(50), default=FestivalDateStatus.UNVERIFIED, nullable=False)  # UNVERIFIED, ESTIMATED, CONFIRMED
    approval_status = Column(String(50), default=FestivalApprovalStatus.PENDING, nullable=False)  # PENDING, APPROVED, REJECTED
    approved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    @property
    def is_verified(self) -> bool:
        """A festival edition is only verified when confirmed and approved by a Manager."""
        return self.date_status == FestivalDateStatus.CONFIRMED and self.approval_status == FestivalApprovalStatus.APPROVED

    # Relationships
    festival = relationship("Festival", back_populates="year_dates")
    approved_by_user = relationship("User", foreign_keys=[approved_by_user_id])
    tasks = relationship("FestivalTask", back_populates="year_date", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("festival_id", "year", name="uq_festival_year"),
        Index("idx_festival_year_dates", "festival_id", "year"),
    )

class FestivalSubcategory(Base):
    """
    Hierarchical festival subcategories under a main Festival.
    Example:
    Festival: Diwali
        -> Subcategory: Diwali Invitation Templates
        -> Subcategory: Diwali Festival Images
        -> Subcategory: Diwali Status Videos
        -> Subcategory: Diwali Poster Images
    """
    __tablename__ = "festival_subcategories"

    id = Column(Integer, primary_key=True, index=True)
    festival_id = Column(Integer, ForeignKey("festivals.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_keywords = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    festival = relationship("Festival", back_populates="subcategories")
    pages = relationship("FestivalPage", back_populates="subcategory")

    __table_args__ = (
        UniqueConstraint("festival_id", "slug", name="uq_festival_subcategory_slug"),
        Index("idx_festival_subcat_fest_id", "festival_id"),
    )

class FestivalPage(Base):
    """
    Mapping between festival subcategories/campaigns and actual landing pages.
    Reuses existing category page references where applicable to prevent URL duplication.
    """
    __tablename__ = "festival_pages"

    id = Column(Integer, primary_key=True, index=True)
    festival_id = Column(Integer, ForeignKey("festivals.id", ondelete="CASCADE"), nullable=False, index=True)
    subcategory_id = Column(Integer, ForeignKey("festival_subcategories.id", ondelete="SET NULL"), nullable=True, index=True)
    category_page_id = Column(Integer, ForeignKey("category_pages.id", ondelete="SET NULL"), nullable=True, index=True)
    full_url = Column(String(1000), nullable=False)
    normalized_url = Column(String(1000), index=True, nullable=False)
    page_title = Column(String(500), nullable=True)
    priority = Column(String(50), default="PRIMARY", nullable=False)  # PRIMARY, SECONDARY, SUPPORTING
    status = Column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, PAUSED, ARCHIVED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    festival = relationship("Festival", back_populates="pages")
    subcategory = relationship("FestivalSubcategory", back_populates="pages")
    category_page = relationship("CategoryPage")
    tasks = relationship("FestivalTask", back_populates="landing_page")

    __table_args__ = (
        UniqueConstraint("festival_id", "normalized_url", name="uq_festival_page_norm_url"),
        Index("idx_festival_page_fest_norm", "festival_id", "normalized_url"),
    )

class FestivalTask(Base):
    """
    Festival preparation workflow tasks tracked across milestone stages.
    Statuses: NOT_STARTED, IN_PROGRESS, READY_FOR_REVIEW, COMPLETED
    Milestone stages: T_MINUS_60, T_MINUS_30, T_MINUS_15, T_MINUS_7, EVENT_DAY, POST_FESTIVAL
    """
    __tablename__ = "festival_tasks"

    id = Column(Integer, primary_key=True, index=True)
    festival_id = Column(Integer, ForeignKey("festivals.id", ondelete="CASCADE"), nullable=False, index=True)
    festival_year_date_id = Column(Integer, ForeignKey("festival_year_dates.id", ondelete="CASCADE"), nullable=True, index=True)
    landing_page_id = Column(Integer, ForeignKey("festival_pages.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(100), default="CONTENT", nullable=False)  # CONTENT, META_TAGS, INTERNAL_LINKS, CREATIVES, TECHNICAL
    milestone_stage = Column(String(50), default="T_MINUS_30", nullable=False)  # T_MINUS_60, T_MINUS_30, T_MINUS_15, T_MINUS_7
    status = Column(String(50), default=FestivalTaskStatus.NOT_STARTED, nullable=False)
    due_date = Column(Date, nullable=True)
    completion_date = Column(DateTime, nullable=True)
    completed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    festival = relationship("Festival", back_populates="tasks")
    year_date = relationship("FestivalYearDate", back_populates="tasks")
    landing_page = relationship("FestivalPage", back_populates="tasks")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    completed_by_user = relationship("User", foreign_keys=[completed_by_user_id])

    __table_args__ = (
        Index("idx_festival_task_status_due", "festival_id", "status", "due_date"),
    )

class FestivalNotification(Base):
    """
    Dashboard-only alerts and milestone reminders for Managers and Team Leaders.
    Supports automatic 30-day, 15-day, 7-day reminders, date approvals, and overdue task notifications.
    Includes built-in duplicate prevention via dedup_key.
    Does NOT send external email, SMS, or WhatsApp.
    """
    __tablename__ = "festival_notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # Null = Broadcast to role
    festival_id = Column(Integer, ForeignKey("festivals.id", ondelete="CASCADE"), nullable=True, index=True)
    year_date_id = Column(Integer, ForeignKey("festival_year_dates.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(Integer, ForeignKey("festival_tasks.id", ondelete="SET NULL"), nullable=True)
    notification_type = Column(String(100), index=True, nullable=False)  # FESTIVAL_30_DAY_REMINDER, etc.
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    action_url = Column(String(1000), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    dedup_key = Column(String(255), index=True, nullable=True)  # Unique hash or key to prevent duplicate notifications
    created_at = Column(DateTime, default=utc_now, nullable=False)
    read_at = Column(DateTime, nullable=True)

    # Relationships
    festival = relationship("Festival", back_populates="notifications")
    recipient_user = relationship("User", foreign_keys=[recipient_user_id])
    task = relationship("FestivalTask")

    __table_args__ = (
        Index("idx_festival_notif_recipient_read", "recipient_user_id", "is_read"),
        Index("idx_festival_notif_dedup", "dedup_key"),
    )

class DailyPageCountryMetrics(Base):
    """
    Additive storage for country-level Google Search Console breakdowns.
    Enables filtering performance by searcher country (e.g. IN, US, GB, CA, AU, AE).
    Worldwide/aggregated metrics remain in `daily_page_metrics` for full backwards compatibility.
    """
    __tablename__ = "daily_page_country_metrics"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("gsc_properties.id"), nullable=True, index=True)
    page_url = Column(String(1000), nullable=False)
    normalized_url = Column(String(1000), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    country_code = Column(String(10), index=True, nullable=False)  # ISO code: 'in', 'us', 'gb', etc.
    clicks = Column(Integer, default=0, nullable=False)
    impressions = Column(Integer, default=0, nullable=False)
    ctr = Column(Float, default=0.0, nullable=False)
    position = Column(Float, default=0.0, nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False)

    property = relationship("GSCProperty")

    __table_args__ = (
        UniqueConstraint("property_id", "normalized_url", "date", "country_code", name="uq_country_metrics_prop_url_date_country"),
        Index("idx_country_metrics_date_normurl", "date", "normalized_url"),
        Index("idx_country_metrics_country_date", "country_code", "date"),
    )

