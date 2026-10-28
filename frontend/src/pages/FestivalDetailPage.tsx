import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  Sparkles, ArrowLeft, Calendar, Plus, ExternalLink, Trash2, Edit2,
  CheckCircle, AlertTriangle, Clock, Check, X, Shield, User, Globe,
  Layers, CheckSquare, BarChart3, TrendingUp, TrendingDown,
  MousePointer, Eye, Percent, Target, AlertCircle, RefreshCw,
  Search, FolderPlus, ListPlus, Copy
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  Tooltip, CartesianGrid, Legend
} from 'recharts';
import { festivalApi } from '../services/festivalApi';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Festival, FestivalYearDate, FestivalSeasonComparisonResponse,
  FestivalBulkPagesResponse, FestivalPageComparison
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

  // Active Tab: 'pages' | 'tasks' | 'gsc' | 'yoy' | 'editions'
  const [activeTab, setActiveTab] = useState<'pages' | 'tasks' | 'gsc' | 'yoy' | 'editions'>('pages');

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

  // Bulk Add Landing Pages Modal
  const [isBulkAddOpen, setIsBulkAddOpen] = useState(false);
  const [bulkUrlsText, setBulkUrlsText] = useState('');
  const [bulkSubcatId, setBulkSubcatId] = useState<number | undefined>(undefined);
  const [bulkPriority, setBulkPriority] = useState<'PRIMARY' | 'SECONDARY' | 'SUPPORTING'>('PRIMARY');
  const [bulkSubmitting, setBulkSubmitting] = useState(false);
  const [bulkResult, setBulkResult] = useState<FestivalBulkPagesResponse | null>(null);
  const [bulkError, setBulkError] = useState<string | null>(null);

  // Single Map Landing Page Modal
  const [isMapPageOpen, setIsMapPageOpen] = useState(false);
  const [mapSubcatId, setMapSubcatId] = useState<number | undefined>(undefined);
  const [mapFullUrl, setMapFullUrl] = useState('');
  const [mapPriority, setMapPriority] = useState<'PRIMARY' | 'SECONDARY' | 'SUPPORTING'>('PRIMARY');
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

  // Filters
  const [pageSearchTerm, setPageSearchTerm] = useState('');
  const [pageSubcatFilter, setPageSubcatFilter] = useState('ALL');
  const [taskPageFilter, setTaskPageFilter] = useState('ALL');

  // ----------------- ANALYTICS STATE -----------------
  const [analyticsCurrentYear, setAnalyticsCurrentYear] = useState<number>(new Date().getFullYear());
  const [analyticsPrevYear, setAnalyticsPrevYear] = useState<number>(new Date().getFullYear() - 1);
  const [analyticsCountry, setAnalyticsCountry] = useState<string>('ALL');
  const [analyticsMetric, setAnalyticsMetric] = useState<'clicks' | 'impressions' | 'ctr' | 'position'>('clicks');
  const [comparisonData, setComparisonData] = useState<FestivalSeasonComparisonResponse | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [festRes, leadersRes] = await Promise.all([
        festivalApi.getFestival(festivalId),
        isManager ? api.getLeaders() : Promise.resolve([]),
      ]);
      setFestival(festRes);
      if (isManager && leadersRes.length > 0) {
        setLeaders(leadersRes);
        setEditLeaderId(festRes.assigned_leader_id || leadersRes[0].id);
      }

      // Prepopulate edit modal state
      setEditName(festRes.name);
      setEditRegion(festRes.region || '');
      setEditDescription(festRes.description || '');

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
    if (festivalId && analyticsCurrentYear) {
      loadAnalytics();
    }
  }, [festivalId, analyticsCurrentYear, analyticsPrevYear, analyticsCountry]);

  // Fast GSC metric lookup by normalized URL
  const metricsMap = useMemo(() => {
    const map = new Map<string, FestivalPageComparison>();
    if (comparisonData?.landing_pages) {
      for (const lp of comparisonData.landing_pages) {
        map.set(lp.normalized_url, lp);
        map.set(lp.page_url, lp);
      }
    }
    return map;
  }, [comparisonData]);

  // ----------------- HANDLERS -----------------
  const handleUpdateFestival = async (e: React.FormEvent) => {
    e.preventDefault();
    setEditSubmitting(true);
    try {
      await festivalApi.updateFestival(festivalId, {
        name: editName.trim(),
        region: editRegion.trim() || undefined,
        description: editDescription.trim() || undefined,
        assigned_leader_id: isManager ? editLeaderId : undefined,
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
    if (!window.confirm(`Are you sure you want to delete '${festival?.name}'? This cannot be undone.`)) {
      return;
    }
    try {
      await festivalApi.deleteFestival(festivalId);
      navigate('/festivals');
    } catch (err: any) {
      alert(err.message || 'Failed to delete festival.');
    }
  };

  const handleAddYearDate = async (e: React.FormEvent) => {
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

  const handleApproveYearDate = async (e: React.FormEvent) => {
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

  const handleAddSubcat = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubcatSubmitting(true);
    try {
      await festivalApi.createSubcategory(festivalId, {
        name: subcatName.trim(),
        slug: subcatSlug.trim() || undefined,
        description: subcatDesc.trim() || undefined,
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

  // Bulk Landing Pages Handler
  const handleBulkAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBulkError(null);
    setBulkResult(null);

    const lines = bulkUrlsText
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean);

    if (lines.length === 0) {
      setBulkError('Please enter at least one URL.');
      return;
    }

    setBulkSubmitting(true);
    try {
      const res = await festivalApi.bulkMapFestivalPages(festivalId, {
        urls: lines,
        subcategory_id: bulkSubcatId || undefined,
        priority: bulkPriority,
      });
      setBulkResult(res);
      if (res.added_count > 0) {
        loadData();
        loadAnalytics();
      }
      if (res.errors.length === 0 && res.warnings.length === 0) {
        setTimeout(() => {
          setIsBulkAddOpen(false);
          setBulkUrlsText('');
          setBulkResult(null);
        }, 1200);
      }
    } catch (err: any) {
      setBulkError(err.message || 'Failed to bulk add landing pages.');
    } finally {
      setBulkSubmitting(false);
    }
  };

  // Single Page Map Handler
  const handleMapPage = async (e: React.FormEvent) => {
    e.preventDefault();
    setMapSubmitting(true);
    try {
      await festivalApi.mapFestivalPage(festivalId, {
        full_url: mapFullUrl.trim(),
        subcategory_id: mapSubcatId || undefined,
        priority: mapPriority,
      });
      setIsMapPageOpen(false);
      setMapFullUrl('');
      loadData();
      loadAnalytics();
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
      loadAnalytics();
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
      setTaskPageId(undefined);
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
    if (!window.confirm('Delete this preparation task?')) return;
    try {
      await festivalApi.deleteFestivalTask(festivalId, taskId);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to delete task.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !festival) {
    return (
      <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-8 text-center max-w-lg mx-auto mt-12">
        <AlertCircle className="w-10 h-10 text-rose-400 mx-auto mb-3" />
        <h3 className="text-base font-bold text-white">Error Loading Festival</h3>
        <p className="text-xs text-slate-400 mt-1">{error || 'Festival not found'}</p>
        <Link
          to="/festivals"
          className="inline-flex items-center space-x-1.5 mt-4 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Festivals</span>
        </Link>
      </div>
    );
  }

  const countryName = COUNTRY_NAMES[festival.country_code] || festival.country_code;
  const flag = COUNTRY_FLAGS[festival.country_code] || '🌐';
  const yearDates = festival.year_dates || [];
  const subcategories = festival.subcategories || [];
  const pages = festival.pages || [];
  const tasks = festival.tasks || [];

  // Sort year dates descending
  const sortedDates = [...yearDates].sort((a, b) => b.year - a.year);
  const latestDate = sortedDates[0];

  // Calculate days remaining to latest start date
  let daysRemaining: number | null = null;
  if (latestDate?.start_date) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const fDate = new Date(latestDate.start_date);
    daysRemaining = Math.ceil((fDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  }

  // Filter landing pages by search and subcategory
  const filteredPages = pages.filter((p) => {
    if (pageSubcatFilter === 'DIRECT' && p.subcategory_id) return false;
    if (pageSubcatFilter !== 'ALL' && pageSubcatFilter !== 'DIRECT') {
      if (p.subcategory_id !== Number(pageSubcatFilter)) return false;
    }
    if (pageSearchTerm) {
      const q = pageSearchTerm.toLowerCase();
      return p.full_url.toLowerCase().includes(q) || (p.page_title && p.page_title.toLowerCase().includes(q));
    }
    return true;
  });

  const bulkLinesCount = bulkUrlsText
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean).length;

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center justify-between">
        <Link
          to="/festivals"
          className="inline-flex items-center space-x-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Festivals</span>
        </Link>

        {isManager && (
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsEditOpen(true)}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
            >
              <Edit2 className="w-3.5 h-3.5 text-indigo-400" />
              <span>Edit Details</span>
            </button>
            <button
              onClick={handleDeleteFestival}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete</span>
            </button>
          </div>
        )}
      </div>

      {/* Festival Hero Header Card */}
      <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 shadow-xl shadow-black/20 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-2xl">{flag}</span>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              {countryName} {festival.region ? `• ${festival.region}` : ''}
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
              {festival.category_group}
            </span>
          </div>

          <h1 className="text-3xl font-bold text-white tracking-tight mt-1">{festival.name}</h1>
          {festival.description && (
            <p className="text-xs text-slate-300 mt-2 max-w-2xl leading-relaxed">{festival.description}</p>
          )}

          <div className="flex flex-wrap items-center gap-4 mt-4 text-xs text-slate-400">
            <div className="flex items-center space-x-1.5">
              <User className="w-4 h-4 text-emerald-400" />
              <span>Assigned: <strong className="text-white">{festival.assigned_leader_name || 'Unassigned'}</strong></span>
            </div>
            <span>•</span>
            <div className="flex items-center space-x-1.5">
              <Layers className="w-4 h-4 text-indigo-400" />
              <span>Landing Pages: <strong className="text-white">{pages.length}</strong></span>
            </div>
            <span>•</span>
            <div className="flex items-center space-x-1.5">
              <CheckSquare className="w-4 h-4 text-purple-400" />
              <span>Preparation Tasks: <strong className="text-white">{tasks.length}</strong></span>
            </div>
          </div>
        </div>

        {/* Edition Dates & Verification Status Card */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/80 md:w-80 shrink-0 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Next Edition:</span>
            <span className="text-sm font-bold text-white">
              {latestDate ? `Edition ${latestDate.year}` : 'No edition set'}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Festival Dates:</span>
            <span className="text-xs font-semibold text-white">
              {latestDate ? `${latestDate.start_date} - ${latestDate.end_date}` : 'Dates TBD'}
            </span>
          </div>

          {daysRemaining !== null && (
            <div className="flex items-center justify-between pt-1 border-t border-slate-800/80">
              <span className="text-xs text-slate-400 font-medium">Timeline:</span>
              <span className={`text-xs font-bold ${daysRemaining < 0 ? 'text-slate-500' : daysRemaining <= 30 ? 'text-rose-400 animate-pulse' : 'text-indigo-400'}`}>
                {daysRemaining < 0 ? 'Concluded' : daysRemaining === 0 ? 'Today!' : `${daysRemaining} days remaining`}
              </span>
            </div>
          )}

          <div className="pt-2 flex items-center justify-between text-[11px]">
            <span className="text-slate-400">Date Status:</span>
            {latestDate?.date_status === 'VERIFIED' ? (
              <span className="inline-flex items-center space-x-1 text-emerald-400 font-bold">
                <CheckCircle className="w-3 h-3" />
                <span>VERIFIED</span>
              </span>
            ) : latestDate?.date_status === 'ESTIMATED' ? (
              <span className="inline-flex items-center space-x-1 text-amber-400 font-bold">
                <Clock className="w-3 h-3" />
                <span>ESTIMATED</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1 text-rose-400 font-bold">
                <AlertTriangle className="w-3 h-3" />
                <span>UNVERIFIED</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Navigation Tabs (Expected Structure) */}
      <div className="flex border-b border-slate-800 space-x-1 overflow-x-auto">
        <button
          onClick={() => setActiveTab('pages')}
          className={`flex items-center space-x-2 py-3 px-4 text-xs font-bold border-b-2 transition-all whitespace-nowrap cursor-pointer ${
            activeTab === 'pages'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Landing Pages ({pages.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('tasks')}
          className={`flex items-center space-x-2 py-3 px-4 text-xs font-bold border-b-2 transition-all whitespace-nowrap cursor-pointer ${
            activeTab === 'tasks'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <CheckSquare className="w-4 h-4" />
          <span>SEO Tasks ({tasks.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('gsc')}
          className={`flex items-center space-x-2 py-3 px-4 text-xs font-bold border-b-2 transition-all whitespace-nowrap cursor-pointer ${
            activeTab === 'gsc'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>GSC Performance</span>
        </button>

        <button
          onClick={() => setActiveTab('yoy')}
          className={`flex items-center space-x-2 py-3 px-4 text-xs font-bold border-b-2 transition-all whitespace-nowrap cursor-pointer ${
            activeTab === 'yoy'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          <span>Year-wise Comparison</span>
        </button>

        <button
          onClick={() => setActiveTab('editions')}
          className={`flex items-center space-x-2 py-3 px-4 text-xs font-bold border-b-2 transition-all whitespace-nowrap cursor-pointer ${
            activeTab === 'editions'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Calendar className="w-4 h-4" />
          <span>Festival Dates ({yearDates.length})</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: LANDING PAGES                                                      */}
      {/* ========================================================================= */}
      {activeTab === 'pages' && (
        <div className="space-y-6">
          {/* Header Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/90 rounded-2xl p-5 border border-slate-800 shadow-xl shadow-black/20">
            <div>
              <div className="flex items-center space-x-2">
                <span className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
                  <Layers className="w-5 h-5" />
                </span>
                <h3 className="text-base font-bold text-white tracking-tight">Landing Pages</h3>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
                  {pages.length} Mapped
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Mapped Crafty Art URLs with real-time GSC performance, SEO task status, and YoY metrics.
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => {
                  setBulkUrlsText('');
                  setBulkResult(null);
                  setBulkError(null);
                  setIsBulkAddOpen(true);
                }}
                className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Add Landing Pages</span>
              </button>

              <button
                onClick={() => setIsAddSubcatOpen(true)}
                className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                title="Optional: Add category groups (e.g. Posters, Wishes, Cards)"
              >
                <FolderPlus className="w-4 h-4 text-slate-400" />
                <span>Add Subcategory</span>
              </button>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search mapped URLs..."
                  value={pageSearchTerm}
                  onChange={(e) => setPageSearchTerm(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              {subcategories.length > 0 && (
                <div className="flex items-center space-x-2 shrink-0">
                  <span className="text-xs text-slate-400 font-medium">Category:</span>
                  <select
                    value={pageSubcatFilter}
                    onChange={(e) => setPageSubcatFilter(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="ALL">All Categories</option>
                    <option value="DIRECT">Direct (No Subcategory)</option>
                    {subcategories.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="text-xs text-slate-400 font-medium">
              Showing <span className="text-white font-bold">{filteredPages.length}</span> of {pages.length} URLs
            </div>
          </div>

          {/* Landing Pages Table */}
          {pages.length === 0 ? (
            <div className="bg-slate-900/90 rounded-2xl p-12 border border-slate-800 text-center">
              <Layers className="w-10 h-10 text-slate-500 mx-auto mb-3" />
              <h4 className="text-base font-bold text-white">No Landing Pages Mapped Yet</h4>
              <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                Map Crafty Art landing page URLs (e.g. /diwali-wishes/templates) directly to {festival.name} to track GSC metrics and SEO preparation.
              </p>
              <button
                onClick={() => {
                  setBulkUrlsText('');
                  setBulkResult(null);
                  setBulkError(null);
                  setIsBulkAddOpen(true);
                }}
                className="mt-5 inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Add Landing Pages</span>
              </button>
            </div>
          ) : filteredPages.length === 0 ? (
            <div className="bg-slate-900/90 rounded-2xl p-8 border border-slate-800 text-center text-xs text-slate-400">
              No landing pages match your search filter.
            </div>
          ) : (
            <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-xl shadow-black/20">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-950/80 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      <th className="py-3 px-4">Landing Page URL</th>
                      <th className="py-3 px-4">Leader</th>
                      <th className="py-3 px-4">SEO Prep Status</th>
                      <th className="py-3 px-4 text-right">Clicks</th>
                      <th className="py-3 px-4 text-right">Impressions</th>
                      <th className="py-3 px-4 text-right">CTR</th>
                      <th className="py-3 px-4 text-right">Avg Position</th>
                      <th className="py-3 px-4 text-right">YoY Performance</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {filteredPages.map((page) => {
                      const pageMetrics = metricsMap.get(page.normalized_url) || metricsMap.get(page.full_url);
                      const pageTasks = tasks.filter((t) => t.landing_page_id === page.id);
                      const completedCount = pageTasks.filter((t) => t.status === 'COMPLETED').length;

                      return (
                        <tr key={page.id} className="hover:bg-slate-800/30 transition-colors">
                          {/* URL & Subcategory */}
                          <td className="py-4 px-4">
                            <div className="flex items-start space-x-2 max-w-md">
                              <a
                                href={page.full_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-semibold text-white hover:text-indigo-400 transition-colors text-xs inline-flex items-center space-x-1.5 break-all"
                              >
                                <span>{page.full_url}</span>
                                <ExternalLink className="w-3 h-3 text-slate-500 shrink-0" />
                              </a>
                            </div>
                            <div className="flex items-center space-x-2 mt-1">
                              {page.subcategory_name ? (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                                  {page.subcategory_name}
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
                                  Direct Festival Page
                                </span>
                              )}
                              <span className="text-[10px] text-slate-500">
                                Priority: <span className="text-slate-400">{page.priority}</span>
                              </span>
                            </div>
                          </td>

                          {/* Assigned Team Leader */}
                          <td className="py-4 px-4 whitespace-nowrap">
                            <div className="flex items-center space-x-1.5 text-xs text-slate-300">
                              <User className="w-3.5 h-3.5 text-emerald-400" />
                              <span>{page.assigned_leader_name || festival.assigned_leader_name || 'Unassigned'}</span>
                            </div>
                          </td>

                          {/* SEO Preparation Status & Tasks */}
                          <td className="py-4 px-4 whitespace-nowrap">
                            <div className="flex items-center space-x-2">
                              {pageTasks.length === 0 ? (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">
                                  No Tasks
                                </span>
                              ) : completedCount === pageTasks.length ? (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center space-x-1">
                                  <CheckCircle className="w-3 h-3" />
                                  <span>{completedCount}/{pageTasks.length} Done</span>
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center space-x-1">
                                  <Clock className="w-3 h-3" />
                                  <span>{completedCount}/{pageTasks.length} In Progress</span>
                                </span>
                              )}

                              <button
                                onClick={() => {
                                  setTaskPageId(page.id);
                                  setTaskTitle(`SEO Task: ${page.full_url.replace(/^https?:\/\/[^/]+/, '')}`);
                                  setIsAddTaskOpen(true);
                                }}
                                className="p-1 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-slate-800 transition-colors"
                                title="Create SEO task for this landing page"
                              >
                                <Plus className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>

                          {/* GSC Clicks */}
                          <td className="py-4 px-4 text-right font-bold text-slate-200 text-xs">
                            {pageMetrics ? pageMetrics.current_clicks.toLocaleString() : '0'}
                          </td>

                          {/* GSC Impressions */}
                          <td className="py-4 px-4 text-right font-medium text-slate-300 text-xs">
                            {pageMetrics ? pageMetrics.current_impressions.toLocaleString() : '0'}
                          </td>

                          {/* CTR */}
                          <td className="py-4 px-4 text-right font-medium text-slate-300 text-xs">
                            {pageMetrics ? `${(pageMetrics.current_ctr * 100).toFixed(1)}%` : '0.0%'}
                          </td>

                          {/* Average Position */}
                          <td className="py-4 px-4 text-right font-semibold text-slate-200 text-xs">
                            {pageMetrics && pageMetrics.current_position > 0 ? pageMetrics.current_position.toFixed(1) : '-'}
                          </td>

                          {/* Year-over-Year Performance */}
                          <td className="py-4 px-4 text-right whitespace-nowrap">
                            {pageMetrics && pageMetrics.click_growth_pct !== null && pageMetrics.click_growth_pct !== undefined ? (
                              <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                pageMetrics.click_growth_pct > 0
                                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                                  : pageMetrics.click_growth_pct < 0
                                  ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                                  : 'bg-slate-800 text-slate-300 border border-slate-700'
                              }`}>
                                {pageMetrics.click_growth_pct > 0 ? (
                                  <TrendingUp className="w-3 h-3" />
                                ) : pageMetrics.click_growth_pct < 0 ? (
                                  <TrendingDown className="w-3 h-3" />
                                ) : null}
                                <span>{pageMetrics.click_growth_pct > 0 ? `+${pageMetrics.click_growth_pct}%` : `${pageMetrics.click_growth_pct}%`} YoY</span>
                              </span>
                            ) : (
                              <span className="text-[10px] text-slate-500">Baseline</span>
                            )}
                          </td>

                          {/* Actions */}
                          <td className="py-4 px-4 text-right">
                            <button
                              onClick={() => handleUnmapPage(page.id)}
                              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                              title="Unmap Landing Page"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: SEO PREPARATION TASKS                                              */}
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

            <div className="flex items-center space-x-2">
              {pages.length > 0 && (
                <div className="flex items-center space-x-1.5">
                  <span className="text-xs text-slate-400 font-medium">Page:</span>
                  <select
                    value={taskPageFilter}
                    onChange={(e) => setTaskPageFilter(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white"
                  >
                    <option value="ALL">All Tasks</option>
                    <option value="FESTIVAL_LEVEL">Festival-Level Only</option>
                    {pages.map((p) => (
                      <option key={p.id} value={p.id.toString()}>
                        {p.full_url.replace(/^https?:\/\/[^/]+/, '')}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <button
                onClick={() => {
                  setTaskPageId(undefined);
                  setIsAddTaskOpen(true);
                }}
                className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Create Task</span>
              </button>
            </div>
          </div>

          {/* Kanban Columns */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              { status: 'NOT_STARTED', title: 'Not Started', badgeColor: 'bg-slate-800 text-slate-400 border-slate-700' },
              { status: 'IN_PROGRESS', title: 'In Progress', badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' },
              { status: 'READY_FOR_REVIEW', title: 'Ready for Review', badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
              { status: 'COMPLETED', title: 'Completed', badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
            ].map((col) => {
              const colTasks = tasks.filter((t) => {
                if (t.status !== col.status) return false;
                if (taskPageFilter === 'ALL') return true;
                if (taskPageFilter === 'FESTIVAL_LEVEL') return !t.landing_page_id;
                return t.landing_page_id === Number(taskPageFilter);
              });

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
                                    className="text-slate-500 hover:text-rose-400 p-0.5 cursor-pointer"
                                  >
                                    <Trash2 className="w-3 h-3" />
                                  </button>
                                )}
                              </div>

                              {t.description && (
                                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{t.description}</p>
                              )}

                              <div className="mt-2.5 pt-2 border-t border-slate-800/80 space-y-1.5 text-[11px]">
                                {t.landing_page_url && (
                                  <div className="flex items-center justify-between text-slate-400">
                                    <span>Page:</span>
                                    <a
                                      href={t.landing_page_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-indigo-400 hover:underline truncate max-w-[140px]"
                                    >
                                      {t.landing_page_url.replace(/^https?:\/\/[^/]+/, '')}
                                    </a>
                                  </div>
                                )}

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
                                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-[11px] text-white focus:outline-none focus:border-indigo-500 cursor-pointer"
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
      {/* TAB 3: GSC PERFORMANCE                                                    */}
      {/* ========================================================================= */}
      {activeTab === 'gsc' && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 font-medium">Current Edition:</span>
                <select
                  value={analyticsCurrentYear}
                  onChange={(e) => setAnalyticsCurrentYear(Number(e.target.value))}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  {yearDates.map((yd) => (
                    <option key={yd.year} value={yd.year}>
                      {yd.year} Edition
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 font-medium">Country:</span>
                <select
                  value={analyticsCountry}
                  onChange={(e) => setAnalyticsCountry(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="ALL">🌐 All Countries (Worldwide)</option>
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
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${analyticsLoading ? 'animate-spin' : ''}`} />
              <span>Refresh GSC</span>
            </button>
          </div>

          {/* GSC Metric KPI Cards */}
          {comparisonData ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase">GSC Clicks</span>
                  <span className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                    <MousePointer className="w-4 h-4" />
                  </span>
                </div>
                <div className="text-2xl font-bold text-white mt-2">
                  {(comparisonData.summary.current_period?.clicks ?? 0).toLocaleString()}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  vs {(comparisonData.summary.previous_period?.clicks ?? 0).toLocaleString()} last edition
                </div>
              </div>

              <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase">GSC Impressions</span>
                  <span className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400">
                    <Eye className="w-4 h-4" />
                  </span>
                </div>
                <div className="text-2xl font-bold text-white mt-2">
                  {(comparisonData.summary.current_period?.impressions ?? 0).toLocaleString()}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  vs {(comparisonData.summary.previous_period?.impressions ?? 0).toLocaleString()} last edition
                </div>
              </div>

              <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase">Average CTR</span>
                  <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                    <Percent className="w-4 h-4" />
                  </span>
                </div>
                <div className="text-2xl font-bold text-white mt-2">
                  {((comparisonData.summary.current_period?.ctr ?? 0) * 100).toFixed(1)}%
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  vs {((comparisonData.summary.previous_period?.ctr ?? 0) * 100).toFixed(1)}% last edition
                </div>
              </div>

              <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase">Average Position</span>
                  <span className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400">
                    <Target className="w-4 h-4" />
                  </span>
                </div>
                <div className="text-2xl font-bold text-white mt-2">
                  {(comparisonData.summary.current_period?.position ?? 0) > 0 ? (comparisonData.summary.current_period.position).toFixed(1) : '-'}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  vs {(comparisonData.summary.previous_period?.position ?? 0) > 0 ? (comparisonData.summary.previous_period.position).toFixed(1) : '-'} last edition
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/90 rounded-2xl p-8 border border-slate-800 text-center text-xs text-slate-400">
              No GSC performance data available for this festival edition yet.
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: YEAR-WISE COMPARISON                                               */}
      {/* ========================================================================= */}
      {activeTab === 'yoy' && (
        <div className="space-y-6">
          <div className="bg-slate-900/90 rounded-2xl p-5 border border-slate-800 shadow-xl shadow-black/20">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-white tracking-tight">Year-over-Year Relative Comparison</h3>
                <p className="text-xs text-slate-400">
                  Anchored comparison window: Day T-30 to Day T+5 relative to festival start date.
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 font-medium">Metric:</span>
                <select
                  value={analyticsMetric}
                  onChange={(e) => setAnalyticsMetric(e.target.value as any)}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white"
                >
                  <option value="clicks">Clicks</option>
                  <option value="impressions">Impressions</option>
                  <option value="ctr">CTR</option>
                  <option value="position">Position</option>
                </select>
              </div>
            </div>

            {/* YoY Chart */}
            {comparisonData && comparisonData.relative_trends.length > 0 ? (
              <div className="mt-4 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={comparisonData.relative_trends}>
                    <defs>
                      <linearGradient id="colorCurrent" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                      </linearGradient>
                      <linearGradient id="colorPrevious" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#94a3b8" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                      dataKey="relative_day_label"
                      stroke="#64748b"
                      fontSize={11}
                      tickLine={false}
                    />
                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#020617', borderColor: '#1e293b', borderRadius: '0.75rem', fontSize: '12px' }}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey={analyticsMetric === 'clicks' ? 'current_clicks' : analyticsMetric === 'impressions' ? 'current_impressions' : analyticsMetric === 'ctr' ? 'current_ctr' : 'current_position'}
                      name={`${analyticsCurrentYear} Edition`}
                      stroke="#6366f1"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorCurrent)"
                    />
                    <Area
                      type="monotone"
                      dataKey={analyticsMetric === 'clicks' ? 'previous_clicks' : analyticsMetric === 'impressions' ? 'previous_impressions' : analyticsMetric === 'ctr' ? 'previous_ctr' : 'previous_position'}
                      name={`${analyticsPrevYear} Edition`}
                      stroke="#94a3b8"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      fillOpacity={1}
                      fill="url(#colorPrevious)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="py-16 text-center text-xs text-slate-500">
                No comparative daily trends available for selected editions.
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 5: FESTIVAL DATES                                                     */}
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
                className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Add Year Edition</span>
              </button>
            )}
          </div>

          <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-xl shadow-black/20">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-950/80 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    <th className="py-3 px-4">Year</th>
                    <th className="py-3 px-4">Festival Dates</th>
                    <th className="py-3 px-4">SEO Prep Window</th>
                    <th className="py-3 px-4">Verification</th>
                    <th className="py-3 px-4">Approval Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {sortedDates.map((yd) => (
                    <tr key={yd.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-4 px-4 font-bold text-white text-xs">{yd.year}</td>
                      <td className="py-4 px-4 text-xs font-medium text-slate-200">
                        {yd.start_date} - {yd.end_date}
                      </td>
                      <td className="py-4 px-4 text-xs text-slate-400">
                        {yd.prep_start_date ? `${yd.prep_start_date} → ${yd.prep_deadline_date || ''}` : 'Default (T-45 → T-15)'}
                      </td>
                      <td className="py-4 px-4">
                        {yd.date_status === 'VERIFIED' ? (
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
                      <td className="py-4 px-4">
                        {yd.approval_status === 'APPROVED' ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                            APPROVED
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                            PENDING REVIEW
                          </span>
                        )}
                      </td>
                      <td className="py-4 px-4 text-right">
                        {isManager && yd.approval_status !== 'APPROVED' && (
                          <button
                            onClick={() => {
                              setApprovingYear(yd);
                              setApprovalDecision('APPROVED');
                              setApprovalNotes('');
                            }}
                            className="px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors cursor-pointer"
                          >
                            Approve
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

      {/* ================= MODAL: BULK ADD LANDING PAGES ================= */}
      {isBulkAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <span className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
                  <Layers className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-white">Add Landing Pages</h3>
                  <p className="text-xs text-slate-400">Paste multiple URLs (one per line). Subcategory is optional.</p>
                </div>
              </div>
              <button onClick={() => setIsBulkAddOpen(false)} className="text-slate-400 hover:text-white cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleBulkAddSubmit} className="mt-4 space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-medium text-slate-300">
                    Landing Page URLs (One per line) *
                  </label>
                  <span className="text-[11px] text-slate-400">
                    {bulkLinesCount} URL{bulkLinesCount !== 1 ? 's' : ''} entered
                  </span>
                </div>
                <textarea
                  rows={6}
                  required
                  placeholder={`https://www.craftyartapp.com/diwali-wishes/templates\nhttps://www.craftyartapp.com/diwali-images-and-poster\nhttps://www.craftyartapp.com/happy-diwali-status-video-download\nhttps://www.craftyartapp.com/dev-diwali-wishes-and-quotes`}
                  value={bulkUrlsText}
                  onChange={(e) => setBulkUrlsText(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Subcategory (Optional)
                  </label>
                  <select
                    value={bulkSubcatId || ''}
                    onChange={(e) => setBulkSubcatId(e.target.value ? Number(e.target.value) : undefined)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">None / General (Direct Festival Page)</option>
                    {subcategories.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Priority</label>
                  <select
                    value={bulkPriority}
                    onChange={(e) => setBulkPriority(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="PRIMARY">PRIMARY (Core Target Pages)</option>
                    <option value="SECONDARY">SECONDARY (Related Designs)</option>
                    <option value="SUPPORTING">SUPPORTING (Long-tail)</option>
                  </select>
                </div>
              </div>

              {bulkResult && (
                <div className={`p-3 rounded-xl border text-xs space-y-1.5 ${
                  bulkResult.added_count > 0 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                }`}>
                  <div className="font-bold flex items-center space-x-1.5">
                    <CheckCircle className="w-4 h-4 shrink-0" />
                    <span>Successfully added {bulkResult.added_count} landing page{bulkResult.added_count !== 1 ? 's' : ''}.</span>
                  </div>
                  {bulkResult.skipped_count > 0 && (
                    <div className="text-[11px] text-amber-300">
                      Skipped {bulkResult.skipped_count} duplicate URL{bulkResult.skipped_count !== 1 ? 's' : ''}.
                    </div>
                  )}
                  {bulkResult.errors.length > 0 && (
                    <div className="text-[11px] text-rose-300">
                      {bulkResult.errors.length} invalid line{bulkResult.errors.length !== 1 ? 's' : ''} skipped.
                    </div>
                  )}
                </div>
              )}

              {bulkError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{bulkError}</span>
                </div>
              )}

              <div className="pt-3 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsBulkAddOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={bulkSubmitting || bulkLinesCount === 0}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition-colors cursor-pointer"
                >
                  {bulkSubmitting ? 'Saving...' : `Save ${bulkLinesCount > 0 ? bulkLinesCount : ''} Pages`}
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
              <button onClick={() => setIsAddTaskOpen(false)} className="text-slate-400 hover:text-white cursor-pointer">
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

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Target Landing Page (Optional)</label>
                <select
                  value={taskPageId || ''}
                  onChange={(e) => setTaskPageId(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">General Festival-Level Task</option>
                  {pages.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.full_url}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Task Type</label>
                  <select
                    value={taskType}
                    onChange={(e) => setTaskType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="CONTENT">Content & On-page</option>
                    <option value="META_TAGS">Meta Tags & Schema</option>
                    <option value="INTERNAL_LINKS">Internal Linking</option>
                    <option value="CREATIVES">Banners & Creatives</option>
                    <option value="TECHNICAL">Technical Audit</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Milestone Stage</label>
                  <select
                    value={taskMilestone}
                    onChange={(e) => setTaskMilestone(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="T_MINUS_60">T-60 Days (Strategy)</option>
                    <option value="T_MINUS_30">T-30 Days (Execution)</option>
                    <option value="T_MINUS_15">T-15 Days (Indexing)</option>
                    <option value="T_MINUS_7">T-7 Days (Final Push)</option>
                    <option value="EVENT_DAY">Event Day</option>
                    <option value="POST_FESTIVAL">Post Festival Review</option>
                  </select>
                </div>
              </div>

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
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Task instructions, keywords, or checklists..."
                  value={taskDesc}
                  onChange={(e) => setTaskDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsAddTaskOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={taskSubmitting}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition-colors cursor-pointer"
                >
                  {taskSubmitting ? 'Creating...' : 'Create Task'}
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
              <button onClick={() => setIsAddSubcatOpen(false)} className="text-slate-400 hover:text-white cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddSubcat} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Subcategory Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Diwali Greeting Cards"
                  value={subcatName}
                  onChange={(e) => {
                    setSubcatName(e.target.value);
                    if (!subcatSlug) {
                      setSubcatSlug(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''));
                    }
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Slug</label>
                <input
                  type="text"
                  placeholder="e.g. diwali-greeting-cards"
                  value={subcatSlug}
                  onChange={(e) => setSubcatSlug(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="SEO themes, key templates..."
                  value={subcatDesc}
                  onChange={(e) => setSubcatDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsAddSubcatOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={subcatSubmitting}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition-colors cursor-pointer"
                >
                  {subcatSubmitting ? 'Creating...' : 'Create Subcategory'}
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
              <h3 className="text-base font-bold text-white">Add Year Calendar Edition</h3>
              <button onClick={() => setIsAddYearOpen(false)} className="text-slate-400 hover:text-white cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddYearDate} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Calendar Year *</label>
                <input
                  type="number"
                  required
                  min={2020}
                  max={2035}
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
                    onChange={(e) => setYearStartDate(e.target.value)}
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

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Verification Status</label>
                <select
                  value={yearDateStatus}
                  onChange={(e) => setYearDateStatus(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="ESTIMATED">ESTIMATED (Approximation)</option>
                  <option value="UNVERIFIED">UNVERIFIED (Requires calendar confirmation)</option>
                  <option value="VERIFIED">VERIFIED (Official gazette)</option>
                </select>
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsAddYearOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={yearSubmitting}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition-colors cursor-pointer"
                >
                  {yearSubmitting ? 'Saving...' : 'Add Edition'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: EDIT FESTIVAL ================= */}
      {isEditOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Edit Festival Details</h3>
              <button onClick={() => setIsEditOpen(false)} className="text-slate-400 hover:text-white cursor-pointer">
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
                <label className="block text-xs font-medium text-slate-300 mb-1">Region</label>
                <input
                  type="text"
                  value={editRegion}
                  onChange={(e) => setEditRegion(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              {isManager && leaders.length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Assigned Team Leader</label>
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
              )}

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  rows={3}
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsEditOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editSubmitting}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition-colors cursor-pointer"
                >
                  {editSubmitting ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
