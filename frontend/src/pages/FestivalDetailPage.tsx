import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  Sparkles, ArrowLeft, Calendar, Plus, ExternalLink, Trash2, Edit2,
  CheckCircle, AlertTriangle, Clock, Check, X, Shield, User, Globe,
  Layers, CheckSquare, BarChart3, TrendingUp, TrendingDown,
  MousePointer, Eye, Percent, Target, AlertCircle, RefreshCw
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  Tooltip, CartesianGrid, Legend
} from 'recharts';
import { festivalApi } from '../services/festivalApi';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Festival, FestivalYearDate, FestivalSeasonComparisonResponse
} from '../types/festival';
import { User as UserType } from '../types';

const COUNTRY_NAMES: Record<string, string> = {
  IN: 'India',
  US: 'USA',
  GB: 'UK',
  CA: 'Canada',
  AU: 'Australia',
  AE: 'UAE',
};

const COUNTRY_FLAGS: Record<string, string> = {
  IN: '🇮🇳',
  US: '🇺🇸',
  GB: '🇬🇧',
  CA: '🇨🇦',
  AU: '🇦🇺',
  AE: '🇦🇪',
};

export const FestivalDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const festivalId = Number(id);
  const navigate = useNavigate();
  const { user, role } = useAuth();
  const isManager = role === 'MANAGER';

  const [festival, setFestival] = useState<Festival | null>(null);
  const [leaders, setLeaders] = useState<UserType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active Tab: 'editions' | 'subcategories' | 'tasks' | 'analytics'
  const [activeTab, setActiveTab] = useState<'editions' | 'subcategories' | 'tasks' | 'analytics'>('analytics');

  // ----------------- MODAL STATES -----------------
  // Edit Festival Modal
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editName, setEditName] = useState('');
  const [editRegion, setEditRegion] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editLeaderId, setEditLeaderId] = useState<number>(1);
  const [editSubmitting, setEditSubmitting] = useState(false);

  // Add Year Edition Modal
  const [isAddYearOpen, setIsAddYearOpen] = useState(false);
  const [yearNum, setYearNum] = useState<number>(new Date().getFullYear() + 1);
  const [yearStartDate, setYearStartDate] = useState('');
  const [yearEndDate, setYearEndDate] = useState('');
  const [yearPrepStart, setYearPrepStart] = useState('');
  const [yearPrepDeadline, setYearPrepDeadline] = useState('');
  const [yearDateStatus, setYearDateStatus] = useState<'VERIFIED' | 'ESTIMATED' | 'UNVERIFIED'>('ESTIMATED');
  const [yearSubmitting, setYearSubmitting] = useState(false);

  // Approve Year Edition Modal
  const [approvingYear, setApprovingYear] = useState<FestivalYearDate | null>(null);
  const [approvalDecision, setApprovalDecision] = useState<'APPROVED' | 'REJECTED'>('APPROVED');
  const [approvalNotes, setApprovalNotes] = useState('');
  const [approvalSubmitting, setApprovalSubmitting] = useState(false);

  // Subcategory Modal
  const [isAddSubcatOpen, setIsAddSubcatOpen] = useState(false);
  const [subcatName, setSubcatName] = useState('');
  const [subcatSlug, setSubcatSlug] = useState('');
  const [subcatDesc, setSubcatDesc] = useState('');
  const [subcatPriority, setSubcatPriority] = useState<'HIGH' | 'MEDIUM' | 'LOW'>('HIGH');
  const [subcatSubmitting, setSubcatSubmitting] = useState(false);

  // Map Landing Page Modal
  const [isMapPageOpen, setIsMapPageOpen] = useState(false);
  const [mapSubcatId, setMapSubcatId] = useState<number | undefined>(undefined);
  const [mapFullUrl, setMapFullUrl] = useState('');
  const [mapCountry, setMapCountry] = useState('ALL');
  const [mapPriority, setMapPriority] = useState<'HIGH' | 'MEDIUM' | 'LOW'>('HIGH');
  const [mapSubmitting, setMapSubmitting] = useState(false);

  // Task Modal
  const [isAddTaskOpen, setIsAddTaskOpen] = useState(false);
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDesc, setTaskDesc] = useState('');
  const [taskType, setTaskType] = useState('CONTENT');
  const [taskMilestone, setTaskMilestone] = useState('T_MINUS_30');
  const [taskDueDate, setTaskDueDate] = useState('');
  const [taskAssigneeId, setTaskAssigneeId] = useState<number>(user?.id || 1);
  const [taskPageId, setTaskPageId] = useState<number | undefined>(undefined);
  const [taskSubmitting, setTaskSubmitting] = useState(false);

  // ----------------- ANALYTICS STATE (Task 5) -----------------
  const [analyticsCurrentYear, setAnalyticsCurrentYear] = useState<number>(new Date().getFullYear());
  const [analyticsPrevYear, setAnalyticsPrevYear] = useState<number>(new Date().getFullYear() - 1);
  const [analyticsCountry, setAnalyticsCountry] = useState<string>('ALL');
  const [analyticsMetric, setAnalyticsMetric] = useState<'clicks' | 'impressions' | 'ctr' | 'position'>('clicks');
  const [comparisonData, setComparisonData] = useState<FestivalSeasonComparisonResponse | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [pageSearchTerm, setPageSearchTerm] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [festRes, leadersRes] = await Promise.all([
        festivalApi.getFestival(festivalId),
        isManager ? api.getLeaders() : Promise.resolve([]),
      ]);
      setFestival(festRes);
      if (isManager) setLeaders(leadersRes);

      // Prepopulate edit modal state
      setEditName(festRes.name);
      setEditRegion(festRes.region || '');
      setEditDescription(festRes.description || '');
      setEditLeaderId(festRes.assigned_leader_id || 1);

      // Set initial analytics years from available year dates
      if (festRes.year_dates && festRes.year_dates.length > 0) {
        const sortedYears = [...festRes.year_dates].sort((a, b) => b.year - a.year);
        const latest = sortedYears[0].year;
        setAnalyticsCurrentYear(latest);
        if (sortedYears.length > 1) {
          setAnalyticsPrevYear(sortedYears[1].year);
        } else {
          setAnalyticsPrevYear(latest - 1);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load festival details.');
    } finally {
      setLoading(false);
    }
  };

  const loadAnalytics = async () => {
    if (!festivalId || !analyticsCurrentYear) return;
    setAnalyticsLoading(true);
    setAnalyticsError(null);
    try {
      const data = await festivalApi.getFestivalYoYComparison(festivalId, analyticsCurrentYear, {
        previous_year: analyticsPrevYear,
        searcher_country: analyticsCountry !== 'ALL' ? analyticsCountry : undefined,
        relative_days_before: 30,
        relative_days_after: 5,
      });
      setComparisonData(data);
    } catch (err: any) {
      setAnalyticsError(err.message || 'Failed to load analytics comparison.');
    } finally {
      setAnalyticsLoading(false);
    }
  };

  useEffect(() => {
    if (festivalId) {
      loadData();
    }
  }, [festivalId]);

  useEffect(() => {
    if (festivalId && activeTab === 'analytics') {
      loadAnalytics();
    }
  }, [festivalId, activeTab, analyticsCurrentYear, analyticsPrevYear, analyticsCountry]);

  // ----------------- HANDLERS -----------------
  const handleUpdateFestival = async (e: React.FormEvent) => {
    e.preventDefault();
    setEditSubmitting(true);
    try {
      await festivalApi.updateFestival(festivalId, {
        name: editName.trim(),
        region: editRegion.trim() || undefined,
        description: editDescription.trim() || undefined,
        assigned_leader_id: editLeaderId,
      });
      setIsEditOpen(false);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to update festival.');
    } finally {
      setEditSubmitting(false);
    }
  };

  const handleDeleteFestival = async () => {
    if (!window.confirm(`Are you sure you want to deactivate or remove festival "${festival?.name}"?`)) {
      return;
    }
    try {
      await festivalApi.deleteFestival(festivalId);
      navigate('/festivals');
    } catch (err: any) {
      alert(err.message || 'Failed to delete festival.');
    }
  };

  const handleAddYearSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setYearSubmitting(true);
    try {
      await festivalApi.addFestivalYearDate(festivalId, {
        year: yearNum,
        start_date: yearStartDate,
        end_date: yearEndDate || yearStartDate,
        prep_start_date: yearPrepStart || undefined,
        prep_deadline_date: yearPrepDeadline || undefined,
        date_status: yearDateStatus,
      });
      setIsAddYearOpen(false);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to add year edition.');
    } finally {
      setYearSubmitting(false);
    }
  };

  const handleApproveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!approvingYear) return;
    setApprovalSubmitting(true);
    try {
      await festivalApi.approveFestivalYearDate(
        festivalId,
        approvingYear.year,
        approvalDecision,
        approvalNotes || undefined
      );
      setApprovingYear(null);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Approval action failed.');
    } finally {
      setApprovalSubmitting(false);
    }
  };

  const handleAddSubcategory = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubcatSubmitting(true);
    try {
      await festivalApi.createSubcategory(festivalId, {
        name: subcatName.trim(),
        slug: subcatSlug.trim() || undefined,
        description: subcatDesc.trim() || undefined,
        priority: subcatPriority,
      });
      setIsAddSubcatOpen(false);
      setSubcatName('');
      setSubcatSlug('');
      setSubcatDesc('');
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to create subcategory.');
    } finally {
      setSubcatSubmitting(false);
    }
  };

  const handleMapPage = async (e: React.FormEvent) => {
    e.preventDefault();
    setMapSubmitting(true);
    try {
      await festivalApi.mapFestivalPage(festivalId, {
        full_url: mapFullUrl.trim(),
        subcategory_id: mapSubcatId || undefined,
        target_country: mapCountry !== 'ALL' ? mapCountry : undefined,
        priority: mapPriority,
      });
      setIsMapPageOpen(false);
      setMapFullUrl('');
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to map landing page.');
    } finally {
      setMapSubmitting(false);
    }
  };

  const handleUnmapPage = async (pageId: number) => {
    if (!window.confirm('Are you sure you want to unmap this landing page from the festival?')) {
      return;
    }
    try {
      await festivalApi.deleteFestivalPage(festivalId, pageId);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to unmap page.');
    }
  };

  const handleAddTask = async (e: React.FormEvent) => {
    e.preventDefault();
    setTaskSubmitting(true);
    try {
      await festivalApi.createFestivalTask(festivalId, {
        title: taskTitle.trim(),
        description: taskDesc.trim() || undefined,
        task_type: taskType,
        milestone_stage: taskMilestone,
        due_date: taskDueDate || undefined,
        assigned_user_id: taskAssigneeId,
        landing_page_id: taskPageId || undefined,
      });
      setIsAddTaskOpen(false);
      setTaskTitle('');
      setTaskDesc('');
      setTaskDueDate('');
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to create task.');
    } finally {
      setTaskSubmitting(false);
    }
  };

  const handleUpdateTaskStatus = async (taskId: number, newStatus: string) => {
    try {
      await festivalApi.updateFestivalTaskStatus(festivalId, taskId, newStatus);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to update task status.');
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    if (!window.confirm('Delete this task?')) return;
    try {
      await festivalApi.deleteFestivalTask(festivalId, taskId);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to delete task.');
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-48 bg-slate-900 rounded-xl" />
        <div className="h-32 bg-slate-900 rounded-2xl" />
        <div className="h-64 bg-slate-900 rounded-2xl" />
      </div>
    );
  }

  if (error || !festival) {
    return (
      <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-8 text-center max-w-xl mx-auto my-12">
        <AlertCircle className="w-10 h-10 text-rose-400 mx-auto mb-3" />
        <h2 className="text-base font-bold text-white">Festival Not Found or Access Denied</h2>
        <p className="text-xs text-slate-400 mt-1">{error || 'You might not have permission to view this festival.'}</p>
        <Link
          to="/festivals"
          className="mt-4 inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Festival Dashboard</span>
        </Link>
      </div>
    );
  }

  const countryName = COUNTRY_NAMES[festival.country_code] || festival.country_code;
  const flag = COUNTRY_FLAGS[festival.country_code] || '🌐';

  // Subcategories & Pages grouping
  const subcategories = festival.subcategories || [];
  const pages = festival.pages || [];
  const tasks = festival.tasks || [];
  const yearDates = festival.year_dates || [];

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation */}
      <div>
        <Link
          to="/festivals"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-400 hover:text-white transition-colors mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Festival Directory</span>
        </Link>

        {/* Festival Header Card */}
        <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 shadow-xl shadow-black/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">{flag}</span>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                {countryName} {festival.region ? `• ${festival.region}` : ''} • {festival.category_group}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight mt-1 flex items-center space-x-2">
              <span>{festival.name}</span>
            </h1>
            {festival.description && (
              <p className="text-xs text-slate-400 mt-1 max-w-2xl">{festival.description}</p>
            )}

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 mt-3 pt-3 border-t border-slate-800/80">
              <span className="flex items-center space-x-1.5">
                <User className="w-3.5 h-3.5 text-indigo-400" />
                <span>Assigned Leader:</span>
                <span className="text-slate-200 font-semibold">{festival.assigned_leader_name || 'Unassigned'}</span>
              </span>

              <span>•</span>

              <span className="flex items-center space-x-1.5">
                <Layers className="w-3.5 h-3.5 text-purple-400" />
                <span className="text-slate-200 font-semibold">{subcategories.length}</span>
                <span>Subcategories</span>
              </span>

              <span>•</span>

              <span className="flex items-center space-x-1.5">
                <Globe className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-slate-200 font-semibold">{pages.length}</span>
                <span>Mapped URLs</span>
              </span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center space-x-2 shrink-0">
            {isManager && (
              <>
                <button
                  onClick={() => setIsEditOpen(true)}
                  className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                  <span>Edit Festival</span>
                </button>

                <button
                  onClick={handleDeleteFestival}
                  className="p-2 rounded-xl text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 transition-colors"
                  title="Deactivate festival"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 space-x-1 overflow-x-auto">
        <button
          onClick={() => setActiveTab('analytics')}
          className={`flex items-center space-x-2 py-3 px-4 text-xs font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'analytics'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>SEO YoY Analytics</span>
        </button>

        <button
          onClick={() => setActiveTab('subcategories')}
          className={`flex items-center space-x-2 py-3 px-4 text-xs font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'subcategories'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Subcategories & URLs ({pages.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('tasks')}
          className={`flex items-center space-x-2 py-3 px-4 text-xs font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'tasks'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <CheckSquare className="w-4 h-4" />
          <span>Preparation Tasks ({tasks.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('editions')}
          className={`flex items-center space-x-2 py-3 px-4 text-xs font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'editions'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Calendar className="w-4 h-4" />
          <span>Year Calendar & Dates ({yearDates.length})</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: SEO YOY ANALYTICS (Task 5)                                         */}
      {/* ========================================================================= */}
      {activeTab === 'analytics' && (
        <div className="space-y-6">
          {/* Analytics Controls Toolbar */}
          <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              {/* Current Year Selection */}
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 font-medium">Target Year:</span>
                <select
                  value={analyticsCurrentYear}
                  onChange={(e) => setAnalyticsCurrentYear(Number(e.target.value))}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  {yearDates.map((yd) => (
                    <option key={yd.year} value={yd.year}>
                      {yd.year} ({yd.start_date})
                    </option>
                  ))}
                  {!yearDates.some((yd) => yd.year === analyticsCurrentYear) && (
                    <option value={analyticsCurrentYear}>{analyticsCurrentYear}</option>
                  )}
                </select>
              </div>

              {/* Baseline Year Selection */}
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 font-medium">Compare with:</span>
                <select
                  value={analyticsPrevYear}
                  onChange={(e) => setAnalyticsPrevYear(Number(e.target.value))}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  {yearDates
                    .filter((yd) => yd.year !== analyticsCurrentYear)
                    .map((yd) => (
                      <option key={yd.year} value={yd.year}>
                        {yd.year} ({yd.start_date})
                      </option>
                    ))}
                  {!yearDates.some((yd) => yd.year === analyticsPrevYear) && (
                    <option value={analyticsPrevYear}>{analyticsPrevYear}</option>
                  )}
                </select>
              </div>

              {/* Country Filtering */}
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 font-medium">Searcher Country:</span>
                <select
                  value={analyticsCountry}
                  onChange={(e) => setAnalyticsCountry(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="ALL">🌐 Worldwide (All)</option>
                  <option value="IN">🇮🇳 India</option>
                  <option value="US">🇺🇸 USA</option>
                  <option value="GB">🇬🇧 UK</option>
                  <option value="CA">🇨🇦 Canada</option>
                  <option value="AU">🇦🇺 Australia</option>
                  <option value="AE">🇦🇪 UAE</option>
                </select>
              </div>
            </div>

            <button
              onClick={loadAnalytics}
              disabled={analyticsLoading}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${analyticsLoading ? 'animate-spin' : ''}`} />
              <span>Refresh Metrics</span>
            </button>
          </div>

          {analyticsLoading ? (
            <div className="h-64 bg-slate-900/60 rounded-2xl animate-pulse border border-slate-800" />
          ) : analyticsError ? (
            <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-6 text-center text-xs text-rose-300">
              <AlertCircle className="w-6 h-6 text-rose-400 mx-auto mb-2" />
              <span>{analyticsError}</span>
            </div>
          ) : comparisonData ? (
            <div className="space-y-6">
              {/* Season Progress Banner */}
              <div
                className={`p-4 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs ${
                  comparisonData.summary.season_status === 'COMPLETE'
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                    : comparisonData.summary.season_status === 'SEASON_TO_DATE'
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                    : 'bg-slate-800/60 border-slate-700 text-slate-300'
                }`}
              >
                <div className="flex items-center space-x-2.5">
                  {comparisonData.summary.season_status === 'COMPLETE' ? (
                    <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
                  ) : (
                    <Clock className="w-5 h-5 text-amber-400 shrink-0" />
                  )}
                  <div>
                    <span className="font-bold">
                      {comparisonData.summary.season_status === 'COMPLETE'
                        ? 'Completed Season Comparison'
                        : comparisonData.summary.season_status === 'SEASON_TO_DATE'
                        ? 'Season-to-Date (In Progress)'
                        : 'Historical Data Range Unavailable'}
                    </span>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Comparing {comparisonData.festival_name} {comparisonData.current_year} (relative day{' '}
                      {comparisonData.summary.relative_window_start_day} to +{comparisonData.summary.relative_window_end_day}) vs{' '}
                      {comparisonData.previous_year} equivalent festival days.
                    </p>
                  </div>
                </div>

                <div className="shrink-0 font-mono text-[11px] bg-slate-900/80 px-3 py-1.5 rounded-xl border border-slate-800 text-slate-200">
                  {comparisonData.summary.searcher_country_label}
                </div>
              </div>

              {/* 4 YoY StatCards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Clicks */}
                <div className="bg-slate-900/90 rounded-2xl p-5 border border-slate-800 shadow-lg shadow-black/20 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">YoY Clicks</span>
                    <span className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
                      <MousePointer className="w-4 h-4" />
                    </span>
                  </div>

                  <div className="my-3">
                    <div className="text-2xl font-bold text-white tracking-tight">
                      {comparisonData.summary.current_period.clicks.toLocaleString()}
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      Prev {comparisonData.previous_year}:{' '}
                      <span className="text-slate-300 font-medium">
                        {comparisonData.summary.previous_period.clicks.toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-1.5">
                      {comparisonData.summary.click_growth_status === 'NEW_TRAFFIC' ? (
                        <span className="px-2 py-0.5 rounded-full font-bold text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                          NEW TRAFFIC
                        </span>
                      ) : comparisonData.summary.click_growth_status === 'NO_BASELINE' ? (
                        <span className="px-2 py-0.5 rounded-full font-bold text-[10px] bg-slate-800 text-slate-400 border border-slate-700">
                          NO BASELINE
                        </span>
                      ) : (
                        <span
                          className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full font-semibold text-[11px] ${
                            (comparisonData.summary.click_growth_pct ?? 0) >= 0
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                              : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                          }`}
                        >
                          {(comparisonData.summary.click_growth_pct ?? 0) >= 0 ? (
                            <TrendingUp className="w-3 h-3" />
                          ) : (
                            <TrendingDown className="w-3 h-3" />
                          )}
                          <span>
                            {(comparisonData.summary.click_growth_pct ?? 0) >= 0 ? '+' : ''}
                            {comparisonData.summary.click_growth_pct?.toFixed(1)}%
                          </span>
                        </span>
                      )}
                    </div>
                    <span className="text-slate-400 font-mono text-[11px]">
                      {comparisonData.summary.click_diff >= 0 ? '+' : ''}
                      {comparisonData.summary.click_diff.toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* Impressions */}
                <div className="bg-slate-900/90 rounded-2xl p-5 border border-slate-800 shadow-lg shadow-black/20 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">YoY Impressions</span>
                    <span className="p-2 rounded-xl bg-purple-500/10 text-purple-400">
                      <Eye className="w-4 h-4" />
                    </span>
                  </div>

                  <div className="my-3">
                    <div className="text-2xl font-bold text-white tracking-tight">
                      {comparisonData.summary.current_period.impressions.toLocaleString()}
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      Prev {comparisonData.previous_year}:{' '}
                      <span className="text-slate-300 font-medium">
                        {comparisonData.summary.previous_period.impressions.toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-1.5">
                      {comparisonData.summary.impression_growth_status === 'NEW_TRAFFIC' ? (
                        <span className="px-2 py-0.5 rounded-full font-bold text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                          NEW TRAFFIC
                        </span>
                      ) : comparisonData.summary.impression_growth_status === 'NO_BASELINE' ? (
                        <span className="px-2 py-0.5 rounded-full font-bold text-[10px] bg-slate-800 text-slate-400 border border-slate-700">
                          NO BASELINE
                        </span>
                      ) : (
                        <span
                          className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full font-semibold text-[11px] ${
                            (comparisonData.summary.impression_growth_pct ?? 0) >= 0
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                              : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                          }`}
                        >
                          {(comparisonData.summary.impression_growth_pct ?? 0) >= 0 ? (
                            <TrendingUp className="w-3 h-3" />
                          ) : (
                            <TrendingDown className="w-3 h-3" />
                          )}
                          <span>
                            {(comparisonData.summary.impression_growth_pct ?? 0) >= 0 ? '+' : ''}
                            {comparisonData.summary.impression_growth_pct?.toFixed(1)}%
                          </span>
                        </span>
                      )}
                    </div>
                    <span className="text-slate-400 font-mono text-[11px]">
                      {comparisonData.summary.impression_diff >= 0 ? '+' : ''}
                      {comparisonData.summary.impression_diff.toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* CTR */}
                <div className="bg-slate-900/90 rounded-2xl p-5 border border-slate-800 shadow-lg shadow-black/20 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Click-Through Rate</span>
                    <span className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
                      <Percent className="w-4 h-4" />
                    </span>
                  </div>

                  <div className="my-3">
                    <div className="text-2xl font-bold text-white tracking-tight">
                      {comparisonData.summary.current_period.ctr.toFixed(2)}%
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      Prev {comparisonData.previous_year}:{' '}
                      <span className="text-slate-300 font-medium">
                        {comparisonData.summary.previous_period.ctr.toFixed(2)}%
                      </span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                    <span
                      className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full font-semibold text-[11px] ${
                        comparisonData.summary.ctr_diff >= 0
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                          : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                      }`}
                    >
                      <span>
                        {comparisonData.summary.ctr_diff >= 0 ? '+' : ''}
                        {comparisonData.summary.ctr_diff.toFixed(2)}% pts
                      </span>
                    </span>
                  </div>
                </div>

                {/* Avg Position */}
                <div className="bg-slate-900/90 rounded-2xl p-5 border border-slate-800 shadow-lg shadow-black/20 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Average Position</span>
                    <span className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
                      <Target className="w-4 h-4" />
                    </span>
                  </div>

                  <div className="my-3">
                    <div className="text-2xl font-bold text-white tracking-tight">
                      {comparisonData.summary.current_period.position > 0
                        ? comparisonData.summary.current_period.position.toFixed(1)
                        : '—'}
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      Prev {comparisonData.previous_year}:{' '}
                      <span className="text-slate-300 font-medium">
                        {comparisonData.summary.previous_period.position > 0
                          ? comparisonData.summary.previous_period.position.toFixed(1)
                          : '—'}
                      </span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                    <span
                      className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full font-semibold text-[11px] ${
                        comparisonData.summary.position_diff <= 0
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                          : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                      }`}
                    >
                      <span>
                        {comparisonData.summary.position_diff <= 0 ? '▲ ' : '▼ '}
                        {Math.abs(comparisonData.summary.position_diff).toFixed(1)} rank
                      </span>
                    </span>
                  </div>
                </div>
              </div>

              {/* Festival-Relative Daily Trends Chart */}
              <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 shadow-xl shadow-black/20">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                  <div>
                    <h3 className="text-base font-bold text-white tracking-tight">
                      Festival-Relative Daily Trajectory
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Timeline anchored on festival start date: Day -30 (preparation peak) to Day +5 (post-event follow through).
                    </p>
                  </div>

                  {/* Metric Switcher */}
                  <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800 self-start sm:self-auto">
                    {[
                      { key: 'clicks', label: 'Clicks' },
                      { key: 'impressions', label: 'Impressions' },
                      { key: 'ctr', label: 'CTR' },
                      { key: 'position', label: 'Position' },
                    ].map((m) => (
                      <button
                        key={m.key}
                        onClick={() => setAnalyticsMetric(m.key as any)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                          analyticsMetric === m.key
                            ? 'bg-indigo-600 text-white shadow-sm'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        {m.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={comparisonData.relative_trends}
                      margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="colorCurrent" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="colorPrev" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#94a3b8" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                      <XAxis
                        dataKey="relative_day"
                        stroke="#64748b"
                        fontSize={11}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(val) => `Day ${val >= 0 ? `+${val}` : val}`}
                      />
                      <YAxis
                        stroke="#64748b"
                        fontSize={11}
                        tickLine={false}
                        axisLine={false}
                        reversed={analyticsMetric === 'position'}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          borderColor: '#334155',
                          borderRadius: '0.75rem',
                          color: '#fff',
                          fontSize: '12px',
                        }}
                        formatter={(val: any) => [
                          analyticsMetric === 'ctr'
                            ? `${val}%`
                            : analyticsMetric === 'position'
                            ? val?.toFixed(1)
                            : val?.toLocaleString(),
                        ]}
                      />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey={
                          analyticsMetric === 'clicks'
                            ? 'current_clicks'
                            : analyticsMetric === 'impressions'
                            ? 'current_impressions'
                            : analyticsMetric === 'ctr'
                            ? 'current_ctr'
                            : 'current_position'
                        }
                        name={`${comparisonData.current_year} (Current)`}
                        stroke="#6366f1"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorCurrent)"
                      />
                      <Area
                        type="monotone"
                        dataKey={
                          analyticsMetric === 'clicks'
                            ? 'previous_clicks'
                            : analyticsMetric === 'impressions'
                            ? 'previous_impressions'
                            : analyticsMetric === 'ctr'
                            ? 'previous_ctr'
                            : 'previous_position'
                        }
                        name={`${comparisonData.previous_year} (Previous)`}
                        stroke="#94a3b8"
                        strokeWidth={2}
                        strokeDasharray="4 4"
                        fillOpacity={1}
                        fill="url(#colorPrev)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Individual Landing Page YoY Comparison Table */}
              <div className="bg-slate-900/90 rounded-2xl border border-slate-800 shadow-xl shadow-black/20 overflow-hidden">
                <div className="p-4 bg-slate-950/60 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-bold text-white">Landing Page Performance Comparison</h4>
                    <p className="text-[11px] text-slate-400">
                      URL-level performance across {comparisonData.current_year} vs {comparisonData.previous_year} season windows.
                    </p>
                  </div>

                  <div className="relative w-full sm:w-64">
                    <input
                      type="text"
                      placeholder="Filter URLs..."
                      value={pageSearchTerm}
                      onChange={(e) => setPageSearchTerm(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/40 text-slate-400 uppercase font-semibold text-[10px] tracking-wider border-b border-slate-800">
                      <tr>
                        <th className="px-4 py-3">Landing Page URL</th>
                        <th className="px-4 py-3 text-right">Clicks ({comparisonData.current_year})</th>
                        <th className="px-4 py-3 text-right">Clicks ({comparisonData.previous_year})</th>
                        <th className="px-4 py-3 text-right">YoY Growth</th>
                        <th className="px-4 py-3 text-right">Impressions</th>
                        <th className="px-4 py-3 text-right">CTR</th>
                        <th className="px-4 py-3 text-right">Avg Pos</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-200">
                      {comparisonData.landing_pages
                        .filter((p) => p.page_url.toLowerCase().includes(pageSearchTerm.toLowerCase()))
                        .map((pageComp) => {
                          return (
                            <tr key={pageComp.page_url} className="hover:bg-slate-800/40 transition-colors">
                              <td className="px-4 py-3 max-w-sm truncate">
                                <a
                                  href={pageComp.page_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="font-medium text-white hover:text-indigo-400 transition-colors inline-flex items-center space-x-1.5"
                                >
                                  <span className="truncate">{pageComp.page_url}</span>
                                  <ExternalLink className="w-3 h-3 text-slate-500 shrink-0" />
                                </a>
                              </td>
                              <td className="px-4 py-3 text-right font-semibold text-white">
                                {pageComp.current_clicks.toLocaleString()}
                              </td>
                              <td className="px-4 py-3 text-right text-slate-400">
                                {pageComp.previous_clicks.toLocaleString()}
                              </td>
                              <td className="px-4 py-3 text-right">
                                {pageComp.click_growth_status === 'NEW_TRAFFIC' ? (
                                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                                    NEW
                                  </span>
                                ) : pageComp.click_growth_status === 'NO_BASELINE' ? (
                                  <span className="text-slate-500 font-mono">—</span>
                                ) : (
                                  <span
                                    className={`font-semibold ${
                                      (pageComp.click_growth_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                                    }`}
                                  >
                                    {(pageComp.click_growth_pct ?? 0) >= 0 ? '+' : ''}
                                    {pageComp.click_growth_pct?.toFixed(1)}%
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-right font-mono text-slate-300">
                                {pageComp.current_impressions.toLocaleString()}
                              </td>
                              <td className="px-4 py-3 text-right font-mono text-slate-300">
                                {pageComp.current_ctr.toFixed(1)}%
                              </td>
                              <td className="px-4 py-3 text-right font-mono text-slate-300">
                                {pageComp.current_position > 0 ? pageComp.current_position.toFixed(1) : '—'}
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: SUBCATEGORIES & MAPPED URLS (Task 4)                              */}
      {/* ========================================================================= */}
      {activeTab === 'subcategories' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">Festival Subcategories & URLs</h3>
              <p className="text-xs text-slate-400">
                Organize distinct festival design categories (e.g. Invitation Templates, Wishes, Posters) and map landing pages.
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setIsAddSubcatOpen(true)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
              >
                <Plus className="w-3.5 h-3.5 text-indigo-400" />
                <span>Add Subcategory</span>
              </button>

              <button
                onClick={() => setIsMapPageOpen(true)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Map Landing Page</span>
              </button>
            </div>
          </div>

          {/* Subcategory List with Mapped Pages */}
          {subcategories.length === 0 ? (
            <div className="bg-slate-900/90 rounded-2xl p-8 border border-slate-800 text-center">
              <Layers className="w-8 h-8 text-slate-500 mx-auto mb-2" />
              <h4 className="text-sm font-bold text-white">No Subcategories Created</h4>
              <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                Create subcategories like "Diwali Invitation Templates" or "Diwali Festival Images" to structure your SEO URLs.
              </p>
              <button
                onClick={() => setIsAddSubcatOpen(true)}
                className="mt-4 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
              >
                Create First Subcategory
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {subcategories.map((subcat) => {
                const subcatPages = pages.filter((p) => p.subcategory_id === subcat.id);

                return (
                  <div
                    key={subcat.id}
                    className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-lg shadow-black/20"
                  >
                    <div className="p-4 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <span className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                          <Layers className="w-4 h-4" />
                        </span>
                        <div>
                          <h4 className="text-sm font-bold text-white">{subcat.name}</h4>
                          {subcat.description && (
                            <p className="text-[11px] text-slate-400 mt-0.5">{subcat.description}</p>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
                          {subcat.slug}
                        </span>
                        <span className="text-xs text-slate-400 font-medium">{subcatPages.length} URLs</span>
                      </div>
                    </div>

                    <div className="divide-y divide-slate-800/60">
                      {subcatPages.length === 0 ? (
                        <div className="p-4 text-xs text-slate-500 text-center">
                          No URLs mapped to this subcategory yet.{' '}
                          <button
                            onClick={() => {
                              setMapSubcatId(subcat.id);
                              setIsMapPageOpen(true);
                            }}
                            className="text-indigo-400 hover:underline ml-1"
                          >
                            Map URL now
                          </button>
                        </div>
                      ) : (
                        subcatPages.map((page) => (
                          <div
                            key={page.id}
                            className="p-3.5 flex items-center justify-between gap-3 text-xs hover:bg-slate-800/30 transition-colors"
                          >
                            <div className="min-w-0 flex-1">
                              <a
                                href={page.full_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-semibold text-white hover:text-indigo-400 transition-colors inline-flex items-center space-x-1.5 truncate max-w-xl"
                              >
                                <span className="truncate">{page.full_url}</span>
                                <ExternalLink className="w-3 h-3 text-slate-500 shrink-0" />
                              </a>
                              <div className="text-[11px] text-slate-400 mt-0.5 flex items-center space-x-2">
                                <span>Priority: <span className="text-slate-300 font-medium">{page.priority}</span></span>
                                <span>•</span>
                                <span>Status: <span className="text-emerald-400 font-medium">{page.status}</span></span>
                              </div>
                            </div>

                            <button
                              onClick={() => handleUnmapPage(page.id)}
                              className="text-slate-500 hover:text-rose-400 transition-colors p-1"
                              title="Unmap URL"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: PREPARATION TASKS (Tasks 4 & 6)                                    */}
      {/* ========================================================================= */}
      {activeTab === 'tasks' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">SEO Preparation Task Board</h3>
              <p className="text-xs text-slate-400">
                Track content optimization, metadata updates, and landing page readiness across milestone stages.
              </p>
            </div>

            <button
              onClick={() => setIsAddTaskOpen(true)}
              className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Create Task</span>
            </button>
          </div>

          {/* Kanban Columns */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              { status: 'NOT_STARTED', title: 'Not Started', badgeColor: 'bg-slate-800 text-slate-400 border-slate-700' },
              { status: 'IN_PROGRESS', title: 'In Progress', badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' },
              { status: 'READY_FOR_REVIEW', title: 'Ready for Review', badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
              { status: 'COMPLETED', title: 'Completed', badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
            ].map((col) => {
              const colTasks = tasks.filter((t) => t.status === col.status);

              return (
                <div
                  key={col.status}
                  className="bg-slate-900/80 rounded-2xl p-4 border border-slate-800 flex flex-col justify-between min-h-[400px]"
                >
                  <div>
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-xs text-white">{col.title}</span>
                        <span className={`px-2 py-0.2 rounded-full text-[10px] font-bold border ${col.badgeColor}`}>
                          {colTasks.length}
                        </span>
                      </div>
                    </div>

                    <div className="mt-3 space-y-3">
                      {colTasks.length === 0 ? (
                        <div className="py-8 text-center text-slate-600 text-[11px]">No tasks</div>
                      ) : (
                        colTasks.map((t) => {
                          const isOverdue =
                            t.due_date &&
                            t.status !== 'COMPLETED' &&
                            new Date(t.due_date) < new Date(new Date().setHours(0, 0, 0, 0));

                          return (
                            <div
                              key={t.id}
                              className={`bg-slate-950 p-3.5 rounded-xl border transition-all ${
                                isOverdue
                                  ? 'border-rose-500/40 shadow-sm shadow-rose-500/10'
                                  : 'border-slate-800 hover:border-slate-700'
                              }`}
                            >
                              <div className="flex items-start justify-between gap-1">
                                <span className="font-bold text-xs text-white leading-tight">{t.title}</span>
                                {isManager && (
                                  <button
                                    onClick={() => handleDeleteTask(t.id)}
                                    className="text-slate-500 hover:text-rose-400 p-0.5"
                                  >
                                    <Trash2 className="w-3 h-3" />
                                  </button>
                                )}
                              </div>

                              {t.description && (
                                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{t.description}</p>
                              )}

                              <div className="mt-2.5 pt-2 border-t border-slate-800/80 space-y-1.5 text-[11px]">
                                <div className="flex items-center justify-between text-slate-400">
                                  <span>Milestone:</span>
                                  <span className="text-slate-300 font-mono text-[10px]">{t.milestone_stage}</span>
                                </div>

                                <div className="flex items-center justify-between text-slate-400">
                                  <span>Assignee:</span>
                                  <span className="text-slate-300 font-medium">
                                    {t.assigned_user_name || 'Unassigned'}
                                  </span>
                                </div>

                                {t.due_date && (
                                  <div className="flex items-center justify-between">
                                    <span className="text-slate-400">Due:</span>
                                    <span
                                      className={`font-semibold ${
                                        isOverdue ? 'text-rose-400' : 'text-slate-300'
                                      }`}
                                    >
                                      {t.due_date} {isOverdue && '(Overdue)'}
                                    </span>
                                  </div>
                                )}
                              </div>

                              {/* Status Transition Selector */}
                              <div className="mt-3">
                                <select
                                  value={t.status}
                                  onChange={(e) => handleUpdateTaskStatus(t.id, e.target.value)}
                                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-[11px] text-white focus:outline-none focus:border-indigo-500"
                                >
                                  <option value="NOT_STARTED">Not Started</option>
                                  <option value="IN_PROGRESS">In Progress</option>
                                  <option value="READY_FOR_REVIEW">Ready for Review</option>
                                  <option value="COMPLETED">Completed</option>
                                </select>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: YEAR EDITIONS & DATES                                              */}
      {/* ========================================================================= */}
      {activeTab === 'editions' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">Year-Specific Calendar Editions</h3>
              <p className="text-xs text-slate-400">
                Multi-year festival dates, date verification tags, and formal manager confirmation history.
              </p>
            </div>

            {isManager && (
              <button
                onClick={() => setIsAddYearOpen(true)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Year Edition</span>
              </button>
            )}
          </div>

          <div className="bg-slate-900/90 rounded-2xl border border-slate-800 shadow-xl shadow-black/20 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/60 text-slate-400 uppercase font-semibold text-[10px] tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Year</th>
                    <th className="px-4 py-3">Dates</th>
                    <th className="px-4 py-3">Verification</th>
                    <th className="px-4 py-3">Approval Status</th>
                    <th className="px-4 py-3">Preparation Window</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-200">
                  {yearDates.map((yd) => (
                    <tr key={yd.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3.5 font-bold text-white text-sm">{yd.year}</td>
                      <td className="px-4 py-3.5">
                        <span className="font-medium text-white">{yd.start_date}</span>
                        {yd.end_date && yd.end_date !== yd.start_date && (
                          <span className="text-slate-400"> to {yd.end_date}</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5">
                        {yd.date_status === 'VERIFIED' || yd.date_status === 'CONFIRMED' ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                            VERIFIED
                          </span>
                        ) : yd.date_status === 'ESTIMATED' ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                            ESTIMATED
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                            UNVERIFIED
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3.5">
                        {yd.approval_status === 'APPROVED' ? (
                          <span className="inline-flex items-center space-x-1 text-emerald-400 font-semibold">
                            <Check className="w-3.5 h-3.5" />
                            <span>Approved</span>
                          </span>
                        ) : yd.approval_status === 'REJECTED' ? (
                          <span className="inline-flex items-center space-x-1 text-rose-400 font-semibold">
                            <X className="w-3.5 h-3.5" />
                            <span>Rejected</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center space-x-1 text-amber-400 font-semibold animate-pulse">
                            <Clock className="w-3.5 h-3.5" />
                            <span>Pending Review</span>
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-slate-400">
                        {yd.prep_start_date ? (
                          <span>
                            {yd.prep_start_date} → {yd.prep_deadline_date || 'Deadline TBD'}
                          </span>
                        ) : (
                          'Not configured'
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        {isManager && yd.approval_status === 'PENDING' && (
                          <button
                            onClick={() => {
                              setApprovingYear(yd);
                              setApprovalDecision('APPROVED');
                              setApprovalNotes('');
                            }}
                            className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 transition-colors"
                          >
                            Review & Approve
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ================= MODAL: EDIT FESTIVAL (Manager Only) ================= */}
      {isEditOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Edit Festival Details</h3>
              <button onClick={() => setIsEditOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateFestival} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Festival Name *</label>
                <input
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Region / State</label>
                <input
                  type="text"
                  value={editRegion}
                  onChange={(e) => setEditRegion(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Assigned Team Leader *</label>
                <select
                  value={editLeaderId}
                  onChange={(e) => setEditLeaderId(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  {leaders.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.full_name} ({l.role})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  rows={3}
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsEditOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editSubmitting}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
                >
                  {editSubmitting ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: ADD YEAR EDITION ================= */}
      {isAddYearOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Add Year Edition</h3>
              <button onClick={() => setIsAddYearOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddYearSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Year *</label>
                <input
                  type="number"
                  required
                  value={yearNum}
                  onChange={(e) => setYearNum(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Start Date *</label>
                  <input
                    type="date"
                    required
                    value={yearStartDate}
                    onChange={(e) => {
                      setYearStartDate(e.target.value);
                      if (!yearEndDate) setYearEndDate(e.target.value);
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">End Date</label>
                  <input
                    type="date"
                    value={yearEndDate}
                    onChange={(e) => setYearEndDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Prep Start Date</label>
                  <input
                    type="date"
                    value={yearPrepStart}
                    onChange={(e) => setYearPrepStart(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Prep Deadline</label>
                  <input
                    type="date"
                    value={yearPrepDeadline}
                    onChange={(e) => setYearPrepDeadline(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Date Status</label>
                <select
                  value={yearDateStatus}
                  onChange={(e) => setYearDateStatus(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="ESTIMATED">ESTIMATED</option>
                  <option value="UNVERIFIED">UNVERIFIED</option>
                  <option value="VERIFIED">VERIFIED</option>
                </select>
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsAddYearOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={yearSubmitting}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
                >
                  {yearSubmitting ? 'Adding...' : 'Add Edition'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: APPROVE YEAR DATES ================= */}
      {approvingYear && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Approve Edition {approvingYear.year}</h3>
              <button onClick={() => setApprovingYear(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleApproveSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Decision</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setApprovalDecision('APPROVED')}
                    className={`py-2 px-3 rounded-xl text-xs font-bold border ${
                      approvalDecision === 'APPROVED'
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    Approve Dates
                  </button>
                  <button
                    type="button"
                    onClick={() => setApprovalDecision('REJECTED')}
                    className={`py-2 px-3 rounded-xl text-xs font-bold border ${
                      approvalDecision === 'REJECTED'
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/50'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    Reject Dates
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Approval Notes</label>
                <textarea
                  rows={2}
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  placeholder="e.g. Verified with Government gazette."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setApprovingYear(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={approvalSubmitting}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
                >
                  {approvalSubmitting ? 'Submitting...' : 'Confirm'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: ADD SUBCATEGORY ================= */}
      {isAddSubcatOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Create Subcategory</h3>
              <button onClick={() => setIsAddSubcatOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddSubcategory} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Subcategory Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Diwali Invitation Templates"
                  value={subcatName}
                  onChange={(e) => setSubcatName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Slug (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. diwali-invitation-templates"
                  value={subcatSlug}
                  onChange={(e) => setSubcatSlug(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Priority</label>
                <select
                  value={subcatPriority}
                  onChange={(e) => setSubcatPriority(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="HIGH">HIGH Priority</option>
                  <option value="MEDIUM">MEDIUM Priority</option>
                  <option value="LOW">LOW Priority</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  rows={2}
                  value={subcatDesc}
                  onChange={(e) => setSubcatDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsAddSubcatOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={subcatSubmitting}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
                >
                  {subcatSubmitting ? 'Creating...' : 'Create Subcategory'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: MAP LANDING PAGE ================= */}
      {isMapPageOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Map Landing Page</h3>
              <button onClick={() => setIsMapPageOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleMapPage} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Full Landing Page URL *</label>
                <input
                  type="url"
                  required
                  placeholder="https://craftyartapp.com/templates/diwali-invitation"
                  value={mapFullUrl}
                  onChange={(e) => setMapFullUrl(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Subcategory (Optional)</label>
                <select
                  value={mapSubcatId || ''}
                  onChange={(e) => setMapSubcatId(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">None / General</option>
                  {subcategories.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Target Country</label>
                  <select
                    value={mapCountry}
                    onChange={(e) => setMapCountry(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="ALL">🌐 Worldwide</option>
                    <option value="IN">🇮🇳 India</option>
                    <option value="US">🇺🇸 USA</option>
                    <option value="GB">🇬🇧 UK</option>
                    <option value="CA">🇨🇦 Canada</option>
                    <option value="AU">🇦🇺 Australia</option>
                    <option value="AE">🇦🇪 UAE</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Priority</label>
                  <select
                    value={mapPriority}
                    onChange={(e) => setMapPriority(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsMapPageOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={mapSubmitting}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
                >
                  {mapSubmitting ? 'Mapping...' : 'Map URL'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: ADD PREPARATION TASK ================= */}
      {isAddTaskOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Create Preparation Task</h3>
              <button onClick={() => setIsAddTaskOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddTask} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Task Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Optimize Diwali template metadata and H1 headers"
                  value={taskTitle}
                  onChange={(e) => setTaskTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Task Type</label>
                  <select
                    value={taskType}
                    onChange={(e) => setTaskType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="CONTENT">Content & Copy</option>
                    <option value="ON_PAGE">On-Page SEO</option>
                    <option value="TECHNICAL">Technical SEO</option>
                    <option value="LINK_BUILDING">Internal Linking</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Milestone Stage</label>
                  <select
                    value={taskMilestone}
                    onChange={(e) => setTaskMilestone(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="T_MINUS_60">T-60 Days</option>
                    <option value="T_MINUS_30">T-30 Days</option>
                    <option value="T_MINUS_15">T-15 Days</option>
                    <option value="T_MINUS_7">T-7 Days</option>
                    <option value="FESTIVAL_WEEK">Festival Week</option>
                    <option value="POST_FESTIVAL">Post Festival</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Due Date</label>
                  <input
                    type="date"
                    value={taskDueDate}
                    onChange={(e) => setTaskDueDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Assignee</label>
                  <select
                    value={taskAssigneeId}
                    onChange={(e) => setTaskAssigneeId(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {isManager ? (
                      leaders.map((l) => (
                        <option key={l.id} value={l.id}>
                          {l.full_name}
                        </option>
                      ))
                    ) : (
                      <option value={user?.id}>{user?.full_name}</option>
                    )}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Related Landing Page (Optional)</label>
                <select
                  value={taskPageId || ''}
                  onChange={(e) => setTaskPageId(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">None / General Task</option>
                  {pages.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.full_url}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  rows={2}
                  value={taskDesc}
                  onChange={(e) => setTaskDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsAddTaskOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={taskSubmitting}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
                >
                  {taskSubmitting ? 'Creating...' : 'Create Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default FestivalDetailPage;
