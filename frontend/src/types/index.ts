export type UserRole = 'MANAGER' | 'TEAM_LEADER';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  category_count?: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  user_id: number;
  full_name: string;
  email: string;
}

export interface SetupStatus {
  is_initialized: boolean;
  manager_exists: boolean;
  system_name: string;
}

export interface PeriodMetrics {
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface ComparisonMetrics {
  current: PeriodMetrics;
  previous: PeriodMetrics;
  click_diff: number;
  click_pct_change: number;
  impression_diff: number;
  impression_pct_change: number;
  ctr_diff: number;
  position_diff: number;
  position_status: 'IMPROVED' | 'DECLINED' | 'STABLE';
}

export interface DailyTrendPoint {
  date: string;
  current_clicks: number;
  current_impressions: number;
  previous_clicks?: number;
  previous_impressions?: number;
  ctr: number;
  position: number;
}

export interface Category {
  id: number;
  name: string;
  description?: string;
  assigned_leader_id: number;
  leader_name?: string;
  leader_email?: string;
  status: string;
  page_count: number;
  created_at: string;
  updated_at: string;
}

export interface CategoryPage {
  id: number;
  category_id: number;
  category_name?: string;
  full_url: string;
  normalized_url: string;
  status: string;
  created_at: string;
  metrics?: ComparisonMetrics;
  active_alerts?: number;
}

export interface Alert {
  id: number;
  page_url: string;
  normalized_url: string;
  category_id?: number;
  category_name?: string;
  assigned_leader_id?: number;
  leader_name?: string;
  alert_type: string;
  severity: 'WARNING' | 'CRITICAL';
  current_value: number;
  previous_value: number;
  pct_change: number;
  detection_date: string;
  period_start?: string;
  period_end?: string;
  status: 'PENDING' | 'REVIEWED' | 'DISMISSED';
  created_at: string;
  reviewed_at?: string;
}

export interface AlertSetting {
  id: number;
  click_warning_pct: number;
  click_critical_pct: number;
  impression_warning_pct: number;
  position_drop_warning: number;
  min_previous_clicks: number;
  min_previous_impressions: number;
  updated_at: string;
}

export interface DashboardKPIs {
  total_leaders: number;
  total_categories: number;
  total_mapped_pages: number;
  current_clicks: number;
  previous_clicks: number;
  click_diff: number;
  click_pct_change: number;
  current_impressions: number;
  previous_impressions: number;
  impression_diff: number;
  impression_pct_change: number;
  current_ctr: number;
  previous_ctr: number;
  current_avg_position: number;
  previous_avg_position: number;
  pages_with_decline: number;
  latest_data_date?: string;
  current_period_label: string;
  previous_period_label: string;
  is_demo_data: boolean;
}

export interface GSCProperty {
  id: number;
  site_url: string;
  permission_level: string;
  is_active: boolean;
  is_demo: boolean;
  is_connected: boolean;
  latest_data_date?: string;
  created_at: string;
}

export interface SyncRun {
  id: number;
  property_id?: number;
  property_site_url?: string;
  triggered_by: string;
  start_time: string;
  end_time?: string;
  status: 'RUNNING' | 'SUCCESS' | 'FAILED' | 'PARTIAL';
  pages_synced: number;
  records_created: number;
  alerts_generated: number;
  latest_data_date?: string;
  error_message?: string;
}

export interface BulkDuplicateCheckItem {
  url: string;
  normalized_url: string;
  is_valid: boolean;
  is_duplicate_in_category: boolean;
  is_mapped_to_other_categories: boolean;
  other_category_names: string[];
  warning?: string;
  error?: string;
}

export interface BulkDuplicateCheckResponse {
  items: BulkDuplicateCheckItem[];
  total_valid: number;
  total_duplicates: number;
  total_warnings: number;
}

export interface PageBulkAddResult {
  added_count: number;
  skipped_count: number;
  pages: CategoryPage[];
  warnings: string[];
  errors: string[];
}

export interface GSCConfigStatus {
  is_configured: boolean;
  client_id_configured: boolean;
  client_secret_configured: boolean;
  client_id?: string;
  redirect_uri: string;
}

