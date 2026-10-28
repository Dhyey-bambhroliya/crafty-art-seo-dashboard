export type DateVerificationStatus = 'CONFIRMED' | 'VERIFIED' | 'ESTIMATED' | 'UNVERIFIED';
export type ApprovalStatus = 'APPROVED' | 'PENDING' | 'REJECTED';
export type TaskStatus = 'NOT_STARTED' | 'IN_PROGRESS' | 'READY_FOR_REVIEW' | 'COMPLETED';
export type MilestoneStage = 'T_MINUS_60' | 'T_MINUS_30' | 'T_MINUS_15' | 'T_MINUS_7' | 'EVENT_DAY' | 'POST_FESTIVAL';
export type TaskType = 'CONTENT' | 'META_TAGS' | 'INTERNAL_LINKS' | 'CREATIVES' | 'TECHNICAL';
export type PagePriority = 'PRIMARY' | 'SECONDARY' | 'SUPPORTING';
export type PageStatus = 'ACTIVE' | 'PAUSED' | 'ARCHIVED';

export interface FestivalYearDate {
  id: number;
  festival_id: number;
  year: number;
  start_date: string;
  end_date: string;
  prep_start_date?: string | null;
  prep_deadline_date?: string | null;
  season_comparison_start?: string | null;
  season_comparison_end?: string | null;
  date_status: DateVerificationStatus;
  approval_status: ApprovalStatus;
  approved_by_user_id?: number | null;
  approved_by_name?: string | null;
  approved_at?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FestivalSubcategory {
  id: number;
  festival_id: number;
  name: string;
  slug: string;
  description?: string | null;
  target_keywords?: string | null;
  created_at: string;
  updated_at: string;
  pages?: FestivalPage[];
}

export interface FestivalPage {
  id: number;
  festival_id: number;
  subcategory_id?: number | null;
  subcategory_name?: string | null;
  category_page_id?: number | null;
  full_url: string;
  normalized_url: string;
  page_title?: string | null;
  priority: PagePriority;
  status: PageStatus;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  task_count?: number;
  completed_task_count?: number;
  seo_status?: string;
  assigned_leader_name?: string | null;
}

export interface FestivalBulkPagesRequest {
  urls: string[];
  subcategory_id?: number | null;
  priority?: PagePriority;
}

export interface FestivalBulkPagesResponse {
  status: string;
  total_submitted: number;
  added_count: number;
  skipped_count: number;
  added_pages: FestivalPage[];
  warnings: string[];
  errors: string[];
}

export interface FestivalTask {
  id: number;
  festival_id: number;
  festival_year_date_id?: number | null;
  landing_page_id?: number | null;
  assigned_user_id?: number | null;
  assigned_user_name?: string | null;
  assigned_user_email?: string | null;
  landing_page_url?: string | null;
  title: string;
  description?: string | null;
  task_type: TaskType;
  milestone_stage: MilestoneStage;
  status: TaskStatus;
  due_date?: string | null;
  completion_date?: string | null;
  completed_by_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Festival {
  id: number;
  name: string;
  slug: string;
  country_code: string;
  region?: string | null;
  category_group: string;
  description?: string | null;
  assigned_leader_id?: number | null;
  assigned_leader_name?: string | null;
  assigned_leader_email?: string | null;
  is_active: boolean;
  upcoming_edition_year?: number | null;
  upcoming_start_date?: string | null;
  upcoming_end_date?: string | null;
  date_status?: DateVerificationStatus | null;
  approval_status?: ApprovalStatus | null;
  page_count: number;
  task_completion_pct: number;
  created_at: string;
  updated_at: string;
  year_dates?: FestivalYearDate[];
  subcategories?: FestivalSubcategory[];
  pages?: FestivalPage[];
  tasks?: FestivalTask[];
}

export interface SuggestedFestival {
  name: string;
  slug: string;
  country_code: string;
  region?: string | null;
  category_group: string;
  calculation_type: string;
  year: number;
  start_date: string;
  end_date: string;
  prep_start_date: string;
  prep_deadline_date: string;
  season_comparison_start: string;
  season_comparison_end: string;
  date_status: DateVerificationStatus;
  approval_status: ApprovalStatus;
  description: string;
  notes?: string | null;
}

export interface FestivalNotification {
  id: number;
  recipient_user_id?: number | null;
  festival_id?: number | null;
  festival_name?: string | null;
  notification_type: string;
  title: string;
  message: string;
  action_url?: string | null;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
}

export interface RelativeDailyTrendPoint {
  relative_day: number;
  current_date?: string | null;
  previous_date?: string | null;
  is_current_available: boolean;
  is_previous_available: boolean;
  current_clicks?: number | null;
  previous_clicks?: number | null;
  current_impressions?: number | null;
  previous_impressions?: number | null;
  current_ctr?: number | null;
  previous_ctr?: number | null;
  current_position?: number | null;
  previous_position?: number | null;
}

export interface FestivalMetricPeriod {
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface FestivalYoYSummary {
  current_year: number;
  previous_year?: number | null;
  season_status: 'COMPLETE' | 'SEASON_TO_DATE' | 'DATA_UNAVAILABLE';
  searcher_country?: string | null;
  searcher_country_label: string;
  country_data_available: boolean;
  relative_window_start_day: number;
  relative_window_end_day: number;
  total_window_days: number;
  compared_days_count: number;
  current_period: FestivalMetricPeriod;
  previous_period: FestivalMetricPeriod;
  click_diff: number;
  click_growth_pct?: number | null;
  click_growth_status: string;
  impression_diff: number;
  impression_growth_pct?: number | null;
  impression_growth_status: string;
  ctr_diff: number;
  position_diff: number;
  position_status: 'IMPROVED' | 'DECLINED' | 'STABLE';
  note?: string | null;
}

export interface FestivalPageComparison {
  page_id?: number | null;
  page_url: string;
  normalized_url: string;
  page_title?: string | null;
  subcategory_id?: number | null;
  subcategory_name?: string | null;
  priority: string;
  current_clicks: number;
  previous_clicks: number;
  click_growth_pct?: number | null;
  click_growth_status: string;
  current_impressions: number;
  previous_impressions: number;
  impression_growth_pct?: number | null;
  impression_growth_status: string;
  current_ctr: number;
  previous_ctr: number;
  ctr_diff: number;
  current_position: number;
  previous_position: number;
  position_diff: number;
  position_status: 'IMPROVED' | 'DECLINED' | 'STABLE';
  daily_trends: RelativeDailyTrendPoint[];
}

export interface FestivalSeasonComparisonResponse {
  festival_id: number;
  festival_name: string;
  festival_slug: string;
  festival_country_code: string;
  current_year: number;
  previous_year?: number | null;
  current_start_date?: string | null;
  previous_start_date?: string | null;
  summary: FestivalYoYSummary;
  landing_pages: FestivalPageComparison[];
  relative_trends: RelativeDailyTrendPoint[];
}

export interface AvailableHistoricalRangeResponse {
  festival_id: number;
  festival_name: string;
  earliest_date?: string | null;
  latest_date?: string | null;
  configured_years: number[];
  supported_searcher_countries: string[];
  mapped_page_count: number;
  note?: string | null;
}
