import {
  AuthResponse, SetupStatus, User, Category, CategoryPage,
  Alert, AlertSetting, DashboardKPIs, DailyTrendPoint, GSCProperty, SyncRun
} from '../types';
const API_ORIGIN = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '');

const BASE_URL = API_ORIGIN
  ? (API_ORIGIN.endsWith('/api') ? API_ORIGIN : `${API_ORIGIN}/api`)
  : '/api';

class ApiClient {
  private getToken(): string | null {
    return localStorage.getItem('crafty_art_auth_token');
  }

  private setToken(token: string): void {
    localStorage.setItem('crafty_art_auth_token', token);
  }

  public clearToken(): void {
    localStorage.removeItem('crafty_art_auth_token');
    localStorage.removeItem('crafty_art_user');
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

    const response = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.clearToken();
      if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/setup')) {
        window.location.href = '/login';
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || errorData.message || `Request failed with status ${response.status}`;
      throw new Error(message);
    }

    return response.json();
  }

  // ---------------- AUTH ----------------
  async getSetupStatus(): Promise<SetupStatus> {
    return this.request<SetupStatus>('/auth/setup-status');
  }

  async setupManager(data: { email: string; full_name: string; password: string }): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>('/auth/setup-manager', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(res.access_token);
    localStorage.setItem('crafty_art_user', JSON.stringify(res));
    return res;
  }

  async login(data: { email: string; password: string }): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(res.access_token);
    localStorage.setItem('crafty_art_user', JSON.stringify(res));
    return res;
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  logout(): void {
    this.clearToken();
    window.location.href = '/login';
  }

  // ---------------- USERS ----------------
  async getUsers(): Promise<User[]> {
    return this.request<User[]>('/users');
  }

  async getLeaders(): Promise<User[]> {
    return this.request<User[]>('/users/leaders');
  }

  async createUser(data: { email: string; full_name: string; password: string; role: string }): Promise<User> {
    return this.request<User>('/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateUser(userId: number, data: Partial<{ email: string; full_name: string; password: string; role: string; is_active: boolean }>): Promise<User> {
    return this.request<User>(`/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteUser(userId: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/users/${userId}`, {
      method: 'DELETE',
    });
  }

  // ---------------- CATEGORIES ----------------
  async getCategories(params?: { leader_id?: number; search?: string; status_filter?: string }): Promise<Category[]> {
    const query = new URLSearchParams();
    if (params?.leader_id) query.append('leader_id', params.leader_id.toString());
    if (params?.search) query.append('search', params.search);
    if (params?.status_filter) query.append('status_filter', params.status_filter);
    return this.request<Category[]>(`/categories?${query.toString()}`);
  }

  async getCategoryDetails(id: number): Promise<any> {
    return this.request<any>(`/categories/${id}`);
  }

  async createCategory(data: { name: string; description?: string; assigned_leader_id: number }): Promise<Category> {
    return this.request<Category>('/categories', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateCategory(id: number, data: Partial<{ name: string; description: string; assigned_leader_id: number; status: string }>): Promise<Category> {
    return this.request<Category>(`/categories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteCategory(id: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/categories/${id}`, {
      method: 'DELETE',
    });
  }

  async checkUrlDuplicate(categoryId: number, url: string): Promise<any> {
    return this.request<any>(`/categories/${categoryId}/pages/check-duplicate`, {
      method: 'POST',
      body: JSON.stringify({ full_url: url }),
    });
  }

  async checkUrlsBulk(categoryId: number, urls: string[]): Promise<any> {
    return this.request<any>(`/categories/${categoryId}/pages/check-duplicates-bulk`, {
      method: 'POST',
      body: JSON.stringify({ urls }),
    });
  }

  async addPageToCategory(categoryId: number, url: string): Promise<CategoryPage> {
    return this.request<CategoryPage>(`/categories/${categoryId}/pages`, {
      method: 'POST',
      body: JSON.stringify({ full_url: url }),
    });
  }

  async addPagesBulk(categoryId: number, urls: string[]): Promise<any> {
    return this.request<any>(`/categories/${categoryId}/pages/bulk`, {
      method: 'POST',
      body: JSON.stringify({ urls }),
    });
  }

  async removePageFromCategory(categoryId: number, pageId: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/categories/${categoryId}/pages/${pageId}`, {
      method: 'DELETE',
    });
  }

  // ---------------- PAGES ----------------
  async getPagesMonitoring(params?: { category_id?: number; leader_id?: number; sort_by?: string; search?: string }): Promise<any[]> {
    const query = new URLSearchParams();
    if (params?.category_id) query.append('category_id', params.category_id.toString());
    if (params?.leader_id) query.append('leader_id', params.leader_id.toString());
    if (params?.sort_by) query.append('sort_by', params.sort_by);
    if (params?.search) query.append('search', params.search);
    return this.request<any[]>(`/pages?${query.toString()}`);
  }

  async getPageDetail(pageId: number): Promise<any> {
    return this.request<any>(`/pages/${pageId}`);
  }

  // ---------------- DASHBOARD ----------------
  async getDashboardKPIs(params?: { leader_id?: number; category_id?: number; property_id?: number }): Promise<DashboardKPIs> {
    const query = new URLSearchParams();
    if (params?.leader_id) query.append('leader_id', params.leader_id.toString());
    if (params?.category_id) query.append('category_id', params.category_id.toString());
    if (params?.property_id) query.append('property_id', params.property_id.toString());
    return this.request<DashboardKPIs>(`/dashboard/kpis?${query.toString()}`);
  }

  async getDashboardTrends(params?: { leader_id?: number; category_id?: number; property_id?: number }): Promise<DailyTrendPoint[]> {
    const query = new URLSearchParams();
    if (params?.leader_id) query.append('leader_id', params.leader_id.toString());
    if (params?.category_id) query.append('category_id', params.category_id.toString());
    if (params?.property_id) query.append('property_id', params.property_id.toString());
    return this.request<DailyTrendPoint[]>(`/dashboard/trends?${query.toString()}`);
  }

  async getCategoriesSummary(leader_id?: number): Promise<any[]> {
    const query = leader_id ? `?leader_id=${leader_id}` : '';
    return this.request<any[]>(`/dashboard/categories-summary${query}`);
  }

  // ---------------- ALERTS ----------------
  async getAlerts(params?: { severity?: string; status_filter?: string; category_id?: number; leader_id?: number }): Promise<Alert[]> {
    const query = new URLSearchParams();
    if (params?.severity) query.append('severity', params.severity);
    if (params?.status_filter) query.append('status_filter', params.status_filter);
    if (params?.category_id) query.append('category_id', params.category_id.toString());
    if (params?.leader_id) query.append('leader_id', params.leader_id.toString());
    return this.request<Alert[]>(`/alerts?${query.toString()}`);
  }

  async updateAlertStatus(alertId: number, status: 'REVIEWED' | 'DISMISSED' | 'PENDING'): Promise<Alert> {
    return this.request<Alert>(`/alerts/${alertId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    });
  }

  async getAlertSettings(): Promise<AlertSetting> {
    return this.request<AlertSetting>('/alerts/settings');
  }

  async updateAlertSettings(data: Partial<AlertSetting>): Promise<AlertSetting> {
    return this.request<AlertSetting>('/alerts/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // ---------------- GSC ----------------
  async getGscConfigStatus(): Promise<any> {
    return this.request<any>('/gsc/config-status');
  }

  async updateGscConfig(data: { client_id: string; client_secret: string; redirect_uri?: string }): Promise<any> {
    return this.request<any>('/gsc/config', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getGscAuthUrl(redirectUri?: string): Promise<{ auth_url: string }> {
    const query = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : '';
    return this.request<{ auth_url: string }>(`/gsc/auth-url${query}`);
  }

  async exchangeGscCode(code: string, redirectUri?: string): Promise<any> {
    return this.request<any>('/gsc/oauth-callback', {
      method: 'POST',
      body: JSON.stringify({ code, redirect_uri: redirectUri }),
    });
  }

  async getGscProperties(): Promise<GSCProperty[]> {
    return this.request<GSCProperty[]>('/gsc/properties');
  }

  async addPropertyManually(data: { site_url: string; permission_level?: string }): Promise<GSCProperty> {
    return this.request<GSCProperty>('/gsc/properties/manual', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async triggerSync(propertyId: number): Promise<any> {
    return this.request<any>(`/gsc/properties/${propertyId}/sync`, {
      method: 'POST',
    });
  }

  async getSyncRuns(propertyId?: number): Promise<SyncRun[]> {
    const query = propertyId ? `?property_id=${propertyId}` : '';
    return this.request<SyncRun[]>(`/gsc/sync-runs${query}`);
  }

  async seedDemoData(): Promise<any> {
    return this.request<any>('/gsc/seed-demo', {
      method: 'POST',
    });
  }

  async purgeDemoData(): Promise<any> {
    return this.request<any>('/gsc/purge-demo', {
      method: 'POST',
    });
  }

  async resetWorkspaceData(): Promise<any> {
    return this.request<any>('/gsc/reset-workspace', {
      method: 'POST',
    });
  }

  async deleteGscProperty(propertyId: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/gsc/properties/${propertyId}`, {
      method: 'DELETE',
    });
  }
}

export const api = new ApiClient();
