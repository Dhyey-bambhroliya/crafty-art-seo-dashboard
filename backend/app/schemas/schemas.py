from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# ----------------- AUTH & USERS -----------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    full_name: str
    email: str

class SetupStatusResponse(BaseModel):
    is_initialized: bool
    manager_exists: bool
    system_name: str = "Crafty Art SEO Management Dashboard"

class SetupManagerRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=100)

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=100)
    role: str = "TEAM_LEADER"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    category_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# ----------------- CATEGORIES & PAGES -----------------
class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    assigned_leader_id: int

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    assigned_leader_id: Optional[int] = None
    status: Optional[str] = None

class PageAddRequest(BaseModel):
    full_url: str
    status: str = "ACTIVE"

class CategoryPageOut(BaseModel):
    id: int
    category_id: int
    category_name: Optional[str] = None
    full_url: str
    normalized_url: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    assigned_leader_id: int
    leader_name: Optional[str] = None
    leader_email: Optional[str] = None
    status: str
    page_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DuplicateCheckResponse(BaseModel):
    normalized_url: str
    is_duplicate_in_category: bool
    is_mapped_to_other_categories: bool
    other_category_names: List[str] = []
    warning_message: Optional[str] = None

class PageBulkAddRequest(BaseModel):
    urls: List[str]

class PageBulkAddResult(BaseModel):
    added_count: int
    skipped_count: int
    pages: List[CategoryPageOut]
    warnings: List[str] = []
    errors: List[str] = []

class BulkDuplicateCheckRequest(BaseModel):
    urls: List[str]

class BulkDuplicateCheckItem(BaseModel):
    url: str
    normalized_url: str
    is_valid: bool
    is_duplicate_in_category: bool
    is_mapped_to_other_categories: bool
    other_category_names: List[str] = []
    warning: Optional[str] = None
    error: Optional[str] = None

class BulkDuplicateCheckResponse(BaseModel):
    items: List[BulkDuplicateCheckItem]
    total_valid: int
    total_duplicates: int
    total_warnings: int

class GSCConfigUpdateRequest(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = None

class GSCConfigStatusResponse(BaseModel):
    is_configured: bool
    client_id_configured: bool
    client_secret_configured: bool
    client_id: Optional[str] = None
    redirect_uri: str

# ----------------- METRICS & COMPARISON -----------------
class PeriodMetrics(BaseModel):
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    position: float = 0.0

class ComparisonMetrics(BaseModel):
    current: PeriodMetrics
    previous: PeriodMetrics
    click_diff: int = 0
    click_pct_change: float = 0.0
    impression_diff: int = 0
    impression_pct_change: float = 0.0
    ctr_diff: float = 0.0
    position_diff: float = 0.0
    position_status: str = "STABLE"  # IMPROVED, DECLINED, STABLE

class DailyTrendPoint(BaseModel):
    date: str
    current_clicks: int = 0
    current_impressions: int = 0
    previous_clicks: Optional[int] = None
    previous_impressions: Optional[int] = None
    position: float = 0.0
    ctr: float = 0.0

class CategorySummary(BaseModel):
    id: int
    name: str
    assigned_leader_id: int
    leader_name: str
    page_count: int
    status: str
    metrics: ComparisonMetrics

class PageSummary(BaseModel):
    id: int
    full_url: str
    normalized_url: str
    category_id: int
    category_name: str
    assigned_leader_id: int
    leader_name: str
    status: str
    metrics: ComparisonMetrics
    active_alerts: int = 0

class DashboardKPIs(BaseModel):
    total_leaders: int
    total_categories: int
    total_mapped_pages: int
    current_clicks: int
    previous_clicks: int
    click_diff: int
    click_pct_change: float
    current_impressions: int
    previous_impressions: int
    impression_diff: int
    impression_pct_change: float
    current_ctr: float
    previous_ctr: float
    current_avg_position: float
    previous_avg_position: float
    pages_with_decline: int
    latest_data_date: Optional[str] = None
    current_period_label: str = "Last 28 Days"
    previous_period_label: str = "Previous 28 Days"
    is_demo_data: bool = False

# ----------------- ALERTS -----------------
class AlertOut(BaseModel):
    id: int
    page_url: str
    normalized_url: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    assigned_leader_id: Optional[int] = None
    leader_name: Optional[str] = None
    alert_type: str
    severity: str
    current_value: float
    previous_value: float
    pct_change: float
    detection_date: date
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AlertStatusUpdate(BaseModel):
    status: str = Field(pattern="^(REVIEWED|DISMISSED|PENDING)$")

class AlertSettingOut(BaseModel):
    id: int
    click_warning_pct: float
    click_critical_pct: float
    impression_warning_pct: float
    position_drop_warning: float
    min_previous_clicks: int
    min_previous_impressions: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AlertSettingUpdate(BaseModel):
    click_warning_pct: Optional[float] = None
    click_critical_pct: Optional[float] = None
    impression_warning_pct: Optional[float] = None
    position_drop_warning: Optional[float] = None
    min_previous_clicks: Optional[int] = None
    min_previous_impressions: Optional[int] = None

# ----------------- GSC & SYNC -----------------
class GSCPropertyOut(BaseModel):
    id: int
    site_url: str
    permission_level: str
    is_active: bool
    is_demo: bool
    is_connected: bool
    latest_data_date: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class GSCAuthUrlOut(BaseModel):
    auth_url: str

class SyncRunOut(BaseModel):
    id: int
    property_id: Optional[int] = None
    property_site_url: Optional[str] = None
    triggered_by: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    pages_synced: int
    records_created: int
    alerts_generated: int
    latest_data_date: Optional[date] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# ----------------- LANDING PAGE TRAFFIC MONITORING -----------------
class TrafficWindowMetrics(BaseModel):
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    position: float = 0.0
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class TrafficComparison(BaseModel):
    current_clicks: int = 0
    previous_clicks: int = 0
    click_diff: int = 0
    pct_change: float = 0.0
    status: str = "NEUTRAL"  # GROWTH, DECLINE, NEUTRAL

class LandingPageTrafficItem(BaseModel):
    id: int
    full_url: str
    normalized_url: str
    category_id: int
    category_name: str
    assigned_leader_id: int
    leader_name: str
    ga4_status: str = "GA4 Required"
    latest_gsc_day_clicks: int = 0
    latest_gsc_date: Optional[str] = None
    traffic_3d: TrafficWindowMetrics
    traffic_7d: TrafficWindowMetrics
    traffic_28d: TrafficWindowMetrics
    comparison_7d: TrafficComparison
    comparison_28d: TrafficComparison
    last_updated: Optional[str] = None

class LandingPageTrafficSummary(BaseModel):
    total_pages_monitored: int = 0
    total_clicks_7d: int = 0
    total_clicks_28d: int = 0
    total_impressions_28d: int = 0
    avg_position_28d: float = 0.0
    growing_pages_count: int = 0
    declining_pages_count: int = 0
    ga4_connected: bool = False
    latest_data_date: Optional[str] = None
    reporting_range_28d: Optional[str] = None
    reporting_range_7d: Optional[str] = None
    reporting_range_3d: Optional[str] = None
    last_sync_time: Optional[str] = None

class LandingPageTrafficResponse(BaseModel):
    items: List[LandingPageTrafficItem]
    total_items: int
    page: int
    page_size: int
    total_pages: int
    summary: LandingPageTrafficSummary
