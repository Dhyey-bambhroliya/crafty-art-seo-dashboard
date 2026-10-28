import {
  Festival, FestivalYearDate, FestivalSubcategory, FestivalPage,
  FestivalTask, FestivalNotification, SuggestedFestival,
  FestivalSeasonComparisonResponse, AvailableHistoricalRangeResponse
} from '../types/festival';

const API_ORIGIN = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '');
const BASE_URL = API_ORIGIN
  ? (API_ORIGIN.endsWith('/api') ? API_ORIGIN : `${API_ORIGIN}/api`)
  : '/api';

class FestivalApiClient {
  private getToken(): string | null {
    return localStorage.getItem('crafty_art_auth_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      localStorage.removeItem('crafty_art_auth_token');
      localStorage.removeItem('crafty_art_user');
      window.dispatchEvent(new Event('auth-unauthorized'));
    }

    if (!res.ok) {
      let errorDetail = 'API request failed';
      try {
        const errorJson = await res.json();
        errorDetail = errorJson.detail || errorJson.message || errorDetail;
      } catch (e) {
        errorDetail = res.statusText || errorDetail;
      }
      throw new Error(errorDetail);
    }

    return res.json() as Promise<T>;
  }

  // ----------------- FESTIVALS CRUD -----------------
  async getFestivals(params: {
    country_code?: string;
    region?: string;
    assigned_leader_id?: number;
    search?: string;
    year?: number;
  } = {}): Promise<Festival[]> {
    const query = new URLSearchParams();
    if (params.country_code && params.country_code !== 'ALL') query.set('country_code', params.country_code);
    if (params.region) query.set('region', params.region);
    if (params.assigned_leader_id) query.set('assigned_leader_id', params.assigned_leader_id.toString());
    if (params.search) query.set('search', params.search);
    if (params.year) query.set('year', params.year.toString());

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Festival[]>(`/festivals${qs}`);
  }

  async getFestival(id: number): Promise<Festival> {
    return this.request<Festival>(`/festivals/${id}`);
  }

  async createFestival(data: any): Promise<Festival> {
    return this.request<Festival>('/festivals', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateFestival(id: number, data: any): Promise<Festival> {
    return this.request<Festival>(`/festivals/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteFestival(id: number): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/festivals/${id}`, {
      method: 'DELETE',
    });
  }

  // ----------------- YEAR EDITIONS & APPROVAL -----------------
  async addFestivalYearDate(id: number, data: any): Promise<FestivalYearDate> {
    return this.request<FestivalYearDate>(`/festivals/${id}/years`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateFestivalYearDate(id: number, year: number, data: any): Promise<FestivalYearDate> {
    return this.request<FestivalYearDate>(`/festivals/${id}/years/${year}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async approveFestivalYearDate(id: number, year: number, approval_status: string, notes?: string): Promise<FestivalYearDate> {
    return this.request<FestivalYearDate>(`/festivals/${id}/years/${year}/approve`, {
      method: 'PUT',
      body: JSON.stringify({ approval_status, notes }),
    });
  }

  // ----------------- COUNTRIES & SUGGESTIONS -----------------
  async getSupportedCountries(): Promise<{ code: string; name: string }[]> {
    return this.request<{ code: string; name: string }[]>('/festivals/countries');
  }

  async getFestivalSuggestions(country_code: string, year: number): Promise<SuggestedFestival[]> {
    return this.request<SuggestedFestival[]>(`/festivals/suggestions?country_code=${encodeURIComponent(country_code)}&year=${year}`);
  }

  async applyFestivalSuggestions(country_code: string, year: number, selected_slugs?: string[]): Promise<any> {
    return this.request<any>('/festivals/suggestions/apply', {
      method: 'POST',
      body: JSON.stringify({ country_code, year, selected_slugs }),
    });
  }

  // ----------------- SUBCATEGORIES & PAGES -----------------
  async createSubcategory(festival_id: number, data: any): Promise<FestivalSubcategory> {
    return this.request<FestivalSubcategory>(`/festivals/${festival_id}/subcategories`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getFestivalPages(festival_id: number): Promise<FestivalPage[]> {
    return this.request<FestivalPage[]>(`/festivals/${festival_id}/pages`);
  }

  async mapFestivalPage(festival_id: number, data: any): Promise<FestivalPage> {
    return this.request<FestivalPage>(`/festivals/${festival_id}/pages`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteFestivalPage(festival_id: number, page_id: number): Promise<any> {
    return this.request<any>(`/festivals/${festival_id}/pages/${page_id}`, {
      method: 'DELETE',
    });
  }

  // ----------------- TASKS -----------------
  async getFestivalTasks(festival_id: number, status?: string, milestone_stage?: string): Promise<FestivalTask[]> {
    const query = new URLSearchParams();
    if (status) query.set('status', status);
    if (milestone_stage) query.set('milestone_stage', milestone_stage);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<FestivalTask[]>(`/festivals/${festival_id}/tasks${qs}`);
  }

  async createFestivalTask(festival_id: number, data: any): Promise<FestivalTask> {
    return this.request<FestivalTask>(`/festivals/${festival_id}/tasks`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateFestivalTask(festival_id: number, task_id: number, data: any): Promise<FestivalTask> {
    return this.request<FestivalTask>(`/festivals/${festival_id}/tasks/${task_id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async updateFestivalTaskStatus(festival_id: number, task_id: number, status: string): Promise<FestivalTask> {
    return this.request<FestivalTask>(`/festivals/${festival_id}/tasks/${task_id}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    });
  }

  async deleteFestivalTask(festival_id: number, task_id: number): Promise<any> {
    return this.request<any>(`/festivals/${festival_id}/tasks/${task_id}`, {
      method: 'DELETE',
    });
  }

  async getOverdueTasks(festival_id?: number): Promise<FestivalTask[]> {
    const qs = festival_id ? `?festival_id=${festival_id}` : '';
    return this.request<FestivalTask[]>(`/festivals/tasks/overdue${qs}`);
  }

  async getAllTasks(params: {
    festival_id?: number;
    status?: string;
    milestone_stage?: string;
  } = {}): Promise<FestivalTask[]> {
    const query = new URLSearchParams();
    if (params.festival_id) query.set('festival_id', params.festival_id.toString());
    if (params.status) query.set('status', params.status);
    if (params.milestone_stage) query.set('milestone_stage', params.milestone_stage);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<FestivalTask[]>(`/festivals/tasks${qs}`);
  }

  // ----------------- YEAR-OVER-YEAR ANALYTICS -----------------
  async getFestivalYoYComparison(festival_id: number, current_year: number, params: {
    previous_year?: number;
    searcher_country?: string;
    relative_days_before?: number;
    relative_days_after?: number;
  } = {}): Promise<FestivalSeasonComparisonResponse> {
    const query = new URLSearchParams();
    query.set('current_year', current_year.toString());
    if (params.previous_year) query.set('previous_year', params.previous_year.toString());
    if (params.searcher_country && params.searcher_country !== 'ALL') query.set('searcher_country', params.searcher_country);
    if (params.relative_days_before !== undefined) query.set('relative_days_before', params.relative_days_before.toString());
    if (params.relative_days_after !== undefined) query.set('relative_days_after', params.relative_days_after.toString());

    return this.request<FestivalSeasonComparisonResponse>(`/festivals/${festival_id}/analytics/comparison?${query.toString()}`);
  }

  async getFestivalHistoricalRanges(festival_id: number): Promise<AvailableHistoricalRangeResponse> {
    return this.request<AvailableHistoricalRangeResponse>(`/festivals/${festival_id}/analytics/available-ranges`);
  }

  // ----------------- NOTIFICATIONS -----------------
  async getNotifications(is_read?: boolean, limit: number = 50, offset: number = 0): Promise<FestivalNotification[]> {
    const query = new URLSearchParams();
    if (is_read !== undefined) query.set('is_read', is_read.toString());
    query.set('limit', limit.toString());
    query.set('offset', offset.toString());

    return this.request<FestivalNotification[]>(`/notifications?${query.toString()}`);
  }

  async getUnreadNotificationCount(): Promise<{ unread_count: number }> {
    return this.request<{ unread_count: number }>('/notifications/unread-count');
  }

  async markNotificationAsRead(id: number): Promise<FestivalNotification> {
    return this.request<FestivalNotification>(`/notifications/${id}/read`, {
      method: 'PUT',
    });
  }

  async markAllNotificationsAsRead(): Promise<{ status: string; marked_read_count: number }> {
    return this.request<{ status: string; marked_read_count: number }>('/notifications/read-all', {
      method: 'PUT',
    });
  }
}

export const festivalApi = new FestivalApiClient();
