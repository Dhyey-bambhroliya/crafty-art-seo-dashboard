from datetime import date, datetime
from typing import List, Optional, Union, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

# ----------------- FESTIVAL YEAR DATES -----------------
class FestivalYearDateBase(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    start_date: date
    end_date: date
    prep_start_date: Optional[date] = None
    prep_deadline_date: Optional[date] = None
    season_comparison_start: Optional[date] = None
    season_comparison_end: Optional[date] = None
    date_status: str = "UNVERIFIED"  # UNVERIFIED, ESTIMATED, CONFIRMED
    notes: Optional[str] = None

class FestivalYearDateCreate(FestivalYearDateBase):
    pass

class FestivalYearDateUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    prep_start_date: Optional[date] = None
    prep_deadline_date: Optional[date] = None
    season_comparison_start: Optional[date] = None
    season_comparison_end: Optional[date] = None
    date_status: Optional[str] = None
    approval_status: Optional[str] = None
    notes: Optional[str] = None

class FestivalDateApprovalRequest(BaseModel):
    approval_status: str = Field(..., description="APPROVED | REJECTED")
    notes: Optional[str] = None

class FestivalYearDateOut(FestivalYearDateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    festival_id: int
    approval_status: str
    approved_by_user_id: Optional[int] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

# ----------------- FESTIVAL SUBCATEGORIES -----------------
class FestivalSubcategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = None
    description: Optional[str] = None
    target_keywords: Optional[str] = None

class FestivalSubcategoryCreate(FestivalSubcategoryBase):
    pass

class FestivalSubcategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    target_keywords: Optional[str] = None

class FestivalSubcategoryOut(FestivalSubcategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    festival_id: int
    slug: str
    created_at: datetime
    updated_at: datetime

# ----------------- FESTIVAL LANDING PAGES -----------------
class FestivalPageBase(BaseModel):
    full_url: Optional[str] = None
    page_url: Optional[str] = None
    subcategory_id: Optional[int] = None
    page_title: Optional[str] = None
    priority: str = "PRIMARY"  # PRIMARY, SECONDARY, SUPPORTING
    status: str = "ACTIVE"  # ACTIVE, PAUSED, ARCHIVED
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def populate_page_url(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("full_url") or data.get("page_url")
            if url:
                data["full_url"] = str(url).strip()
                data["page_url"] = str(url).strip()
        elif hasattr(data, "full_url"):
            data.page_url = data.full_url
        return data

class FestivalPageCreate(FestivalPageBase):
    category_page_id: Optional[int] = None

class FestivalPageUpdate(BaseModel):
    subcategory_id: Optional[int] = None
    page_title: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class FestivalPageOut(FestivalPageBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    festival_id: int
    full_url: str
    page_url: Optional[str] = None
    normalized_url: str
    subcategory_name: Optional[str] = None
    category_page_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    task_count: int = 0
    completed_task_count: int = 0
    seo_status: str = "NOT_STARTED"
    assigned_leader_name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_page_url(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("full_url") or data.get("page_url")
            if url:
                data["full_url"] = str(url).strip()
                data["page_url"] = str(url).strip()
        elif hasattr(data, "full_url"):
            setattr(data, "page_url", getattr(data, "full_url"))
        return data

class FestivalBulkPagesRequest(BaseModel):
    urls: List[str] = Field(default_factory=list)
    urls_text: Optional[str] = None
    subcategory_id: Optional[int] = None
    priority: str = "PRIMARY"
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def extract_urls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_urls = data.get("urls")
            urls_text = data.get("urls_text")
            extracted: List[str] = []
            if isinstance(raw_urls, list):
                extracted.extend([str(u).strip() for u in raw_urls if str(u).strip()])
            if isinstance(urls_text, str) and urls_text.strip():
                extracted.extend([line.strip() for line in urls_text.splitlines() if line.strip()])
            data["urls"] = extracted
        return data

class FestivalBulkPagesResponse(BaseModel):
    status: str
    total_submitted: int
    added_count: int
    skipped_count: int
    duplicate_count: int = 0
    invalid_count: int = 0
    added_pages: List[FestivalPageOut] = []
    warnings: List[str] = []
    errors: List[str] = []

class FestivalPageDuplicateCheckResponse(BaseModel):
    normalized_url: str
    is_duplicate_in_festival: bool
    is_mapped_to_existing_category: bool
    existing_category_name: Optional[str] = None
    warning: Optional[str] = None

# ----------------- FESTIVAL PREPARATION TASKS -----------------
class FestivalTaskBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=500)
    description: Optional[str] = None
    task_type: str = "CONTENT"  # CONTENT, META_TAGS, INTERNAL_LINKS, CREATIVES, TECHNICAL
    milestone_stage: str = "T_MINUS_30"  # T_MINUS_60, T_MINUS_30, T_MINUS_15, T_MINUS_7, EVENT_DAY, POST_FESTIVAL
    status: str = "NOT_STARTED"
    due_date: Optional[date] = None
    landing_page_id: Optional[int] = None
    festival_year_date_id: Optional[int] = None
    assigned_user_id: Optional[int] = None

class FestivalTaskCreate(FestivalTaskBase):
    pass

class FestivalTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[str] = None
    milestone_stage: Optional[str] = None
    status: Optional[str] = None  # NOT_STARTED, IN_PROGRESS, READY_FOR_REVIEW, COMPLETED
    due_date: Optional[date] = None
    landing_page_id: Optional[int] = None
    assigned_user_id: Optional[int] = None

class FestivalTaskStatusUpdate(BaseModel):
    status: str = Field(..., description="NOT_STARTED | IN_PROGRESS | READY_FOR_REVIEW | COMPLETED")

class FestivalTaskOut(FestivalTaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    festival_id: int
    status: str
    assigned_user_name: Optional[str] = None
    assigned_user_email: Optional[str] = None
    landing_page_url: Optional[str] = None
    completion_date: Optional[datetime] = None
    completed_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# ----------------- FESTIVAL CORE -----------------
class FestivalBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    country_code: str = Field("IN", min_length=2, max_length=10)
    region: Optional[str] = None
    category_group: str = "Cultural"
    description: Optional[str] = None
    assigned_leader_id: Optional[int] = None
    is_active: bool = True

class FestivalCreate(FestivalBase):
    slug: Optional[str] = None
    initial_year_date: Optional[FestivalYearDateCreate] = None
    initial_year: Optional[int] = None
    start_date: Optional[Union[date, str]] = None
    end_date: Optional[Union[date, str]] = None
    date_status: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def assemble_initial_year_date(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If flat fields provided from form but initial_year_date is missing, construct it
            start_val = data.get("start_date")
            yr_val = data.get("initial_year")
            if not data.get("initial_year_date") and (start_val or yr_val):
                if start_val:
                    end_val = data.get("end_date") or start_val
                    parsed_yr = yr_val
                    if not parsed_yr and isinstance(start_val, str) and len(start_val) >= 4:
                        try:
                            parsed_yr = int(start_val[:4])
                        except ValueError:
                            parsed_yr = datetime.now().year
                    elif not parsed_yr:
                        parsed_yr = datetime.now().year
                    data["initial_year_date"] = {
                        "year": parsed_yr,
                        "start_date": start_val,
                        "end_date": end_val,
                        "date_status": data.get("date_status") or "ESTIMATED"
                    }
        return data

class FestivalUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    category_group: Optional[str] = None
    description: Optional[str] = None
    assigned_leader_id: Optional[int] = None
    is_active: Optional[bool] = None

class FestivalOut(FestivalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    assigned_leader_name: Optional[str] = None
    assigned_leader_email: Optional[str] = None
    upcoming_edition_year: Optional[int] = None
    upcoming_start_date: Optional[date] = None
    upcoming_end_date: Optional[date] = None
    date_status: Optional[str] = None
    approval_status: Optional[str] = None
    page_count: int = 0
    task_completion_pct: float = 0.0
    created_at: datetime
    updated_at: datetime

class FestivalDetailOut(FestivalOut):
    year_dates: List[FestivalYearDateOut] = []
    subcategories: List[FestivalSubcategoryOut] = []
    pages: List[FestivalPageOut] = []
    tasks: List[FestivalTaskOut] = []

# ----------------- NOTIFICATIONS -----------------
class FestivalNotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_user_id: Optional[int] = None
    festival_id: Optional[int] = None
    festival_name: Optional[str] = None
    notification_type: str
    title: str
    message: str
    action_url: Optional[str] = None
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

class FestivalNotificationStatusUpdate(BaseModel):
    is_read: bool = True

class UnreadCountResponse(BaseModel):
    unread_count: int

# ----------------- SUGGESTIONS -----------------
class SuggestedFestivalOut(BaseModel):
    name: str
    slug: str
    country_code: str
    region: Optional[str] = None
    category_group: str
    calculation_type: str
    year: int
    start_date: date
    end_date: date
    prep_start_date: date
    prep_deadline_date: date
    season_comparison_start: date
    season_comparison_end: date
    date_status: str
    approval_status: str
    description: str
    notes: Optional[str] = None

class ApplySuggestionsRequest(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=10)
    year: int = Field(..., ge=2000, le=2100)
    selected_slugs: Optional[List[str]] = None

class ApplySuggestionsResponse(BaseModel):
    status: str
    created_festivals: int
    created_year_dates: int
    skipped_existing: int

# ----------------- YEAR-OVER-YEAR ANALYTICS -----------------
class RelativeDailyTrendPoint(BaseModel):
    relative_day: int
    current_date: Optional[date] = None
    previous_date: Optional[date] = None
    is_current_available: bool = False
    is_previous_available: bool = False
    current_clicks: Optional[int] = None
    previous_clicks: Optional[int] = None
    current_impressions: Optional[int] = None
    previous_impressions: Optional[int] = None
    current_ctr: Optional[float] = None
    previous_ctr: Optional[float] = None
    current_position: Optional[float] = None
    previous_position: Optional[float] = None

class FestivalMetricPeriod(BaseModel):
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    position: float = 0.0

class FestivalYoYSummary(BaseModel):
    current_year: int
    previous_year: Optional[int] = None
    season_status: str  # COMPLETE, SEASON_TO_DATE, DATA_UNAVAILABLE
    searcher_country: Optional[str] = None
    searcher_country_label: str = "Worldwide"
    country_data_available: bool = True
    relative_window_start_day: int = -30
    relative_window_end_day: int = 5
    total_window_days: int = 36
    compared_days_count: int = 0
    current_period: FestivalMetricPeriod
    previous_period: FestivalMetricPeriod
    click_diff: int = 0
    click_growth_pct: Optional[float] = None
    click_growth_status: str = "NO_BASELINE"
    impression_diff: int = 0
    impression_growth_pct: Optional[float] = None
    impression_growth_status: str = "NO_BASELINE"
    ctr_diff: float = 0.0
    position_diff: float = 0.0
    position_status: str = "STABLE"  # IMPROVED, DECLINED, STABLE
    note: Optional[str] = None

class FestivalPageComparison(BaseModel):
    page_id: Optional[int] = None
    page_url: str
    normalized_url: str
    page_title: Optional[str] = None
    subcategory_id: Optional[int] = None
    subcategory_name: Optional[str] = None
    priority: str = "PRIMARY"
    current_clicks: int = 0
    previous_clicks: int = 0
    click_growth_pct: Optional[float] = None
    click_growth_status: str = "NO_BASELINE"
    current_impressions: int = 0
    previous_impressions: int = 0
    impression_growth_pct: Optional[float] = None
    impression_growth_status: str = "NO_BASELINE"
    current_ctr: float = 0.0
    previous_ctr: float = 0.0
    ctr_diff: float = 0.0
    current_position: float = 0.0
    previous_position: float = 0.0
    position_diff: float = 0.0
    position_status: str = "STABLE"
    daily_trends: List[RelativeDailyTrendPoint] = []

class FestivalSeasonComparisonResponse(BaseModel):
    festival_id: int
    festival_name: str
    festival_slug: str
    festival_country_code: str
    current_year: int
    previous_year: Optional[int] = None
    current_start_date: Optional[date] = None
    previous_start_date: Optional[date] = None
    summary: FestivalYoYSummary
    landing_pages: List[FestivalPageComparison] = []
    relative_trends: List[RelativeDailyTrendPoint] = []

class AvailableHistoricalRangeResponse(BaseModel):
    festival_id: int
    festival_name: str
    earliest_date: Optional[date] = None
    latest_date: Optional[date] = None
    configured_years: List[int] = []
    supported_searcher_countries: List[str] = []
    mapped_page_count: int = 0
    note: Optional[str] = None

