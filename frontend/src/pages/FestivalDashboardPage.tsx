import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles, Plus, Calendar, Filter, Search, CheckCircle, AlertTriangle,
  AlertCircle, Clock, Check, X, Shield, User, Globe, ArrowRight,
  RefreshCw, CheckSquare, Layers, Eye, ChevronRight
} from 'lucide-react';
import { festivalApi } from '../services/festivalApi';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Festival, SuggestedFestival } from '../types/festival';
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

export const FestivalDashboardPage: React.FC = () => {
  const { user, role } = useAuth();
  const isManager = role === 'MANAGER';

  const [festivals, setFestivals] = useState<Festival[]>([]);
  const [leaders, setLeaders] = useState<UserType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [countryFilter, setCountryFilter] = useState<string>('ALL');
  const [yearFilter, setYearFilter] = useState<number>(new Date().getFullYear());
  const [leaderFilter, setLeaderFilter] = useState<number | undefined>(undefined);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'PENDING' | 'VERIFIED' | 'ESTIMATED'>('ALL');

  // Stats
  const [totalCount, setTotalCount] = useState(0);
  const [upcomingCount, setUpcomingCount] = useState(0);
  const [pendingApprovalCount, setPendingApprovalCount] = useState(0);
  const [overdueCount, setOverdueCount] = useState(0);
  const [activeTaskCount, setActiveTaskCount] = useState(0);

  // Modals
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isSuggestionsOpen, setIsSuggestionsOpen] = useState(false);
  const [isApproveOpen, setIsApproveOpen] = useState(false);
  const [selectedFestivalForApproval, setSelectedFestivalForApproval] = useState<Festival | null>(null);

  // Form states for Add Festival
  const [addName, setAddName] = useState('');
  const [addCountry, setAddCountry] = useState('IN');
  const [addRegion, setAddRegion] = useState('');
  const [addDescription, setAddDescription] = useState('');
  const [addCategoryGroup, setAddCategoryGroup] = useState('RELIGIOUS');
  const [addLeaderId, setAddLeaderId] = useState<number>(user?.id || 1);
  const [addYear, setAddYear] = useState(new Date().getFullYear());
  const [addStartDate, setAddStartDate] = useState('');
  const [addEndDate, setAddEndDate] = useState('');
  const [addDateStatus, setAddDateStatus] = useState<'VERIFIED' | 'ESTIMATED' | 'UNVERIFIED'>('ESTIMATED');
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Suggestions state
  const [sugCountry, setSugCountry] = useState('IN');
  const [sugYear, setSugYear] = useState(new Date().getFullYear());
  const [suggestions, setSuggestions] = useState<SuggestedFestival[]>([]);
  const [selectedSugSlugs, setSelectedSugSlugs] = useState<string[]>([]);
  const [sugLoading, setSugLoading] = useState(false);
  const [sugApplying, setSugApplying] = useState(false);
  const [sugSuccessMsg, setSugSuccessMsg] = useState<string | null>(null);

  // Approval modal state
  const [approvalDecision, setApprovalDecision] = useState<'APPROVED' | 'REJECTED'>('APPROVED');
  const [approvalNotes, setApprovalNotes] = useState('');
  const [approvalLoading, setApprovalLoading] = useState(false);

  const loadFestivals = async () => {
    setLoading(true);
    setError(null);
    try {
      const [fests, leadersRes, overdueTasks, allTasks] = await Promise.all([
        festivalApi.getFestivals({
          country_code: countryFilter !== 'ALL' ? countryFilter : undefined,
          assigned_leader_id: isManager ? leaderFilter : undefined,
          search: searchTerm || undefined,
          year: yearFilter || undefined,
        }),
        isManager ? api.getLeaders() : Promise.resolve([]),
        festivalApi.getOverdueTasks().catch(() => []),
        festivalApi.getAllTasks().catch(() => []),
      ]);

      setFestivals(fests);
      if (isManager) {
        setLeaders(leadersRes);
      }

      // Compute overview stats
      setTotalCount(fests.length);
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const upcoming = fests.filter((f) => {
        if (!f.upcoming_start_date) return false;
        const d = new Date(f.upcoming_start_date);
        const diffDays = Math.ceil((d.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
        return diffDays >= 0 && diffDays <= 60;
      });
      setUpcomingCount(upcoming.length);

      const pending = fests.filter((f) => f.approval_status === 'PENDING');
      setPendingApprovalCount(pending.length);

      setOverdueCount(overdueTasks.length);
      const activeTasks = allTasks.filter((t) => t.status !== 'COMPLETED');
      setActiveTaskCount(activeTasks.length);
    } catch (err: any) {
      setError(err.message || 'Failed to load festivals.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFestivals();
  }, [countryFilter, yearFilter, leaderFilter, searchTerm]);

  // Handle Add Festival submit
  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSubmitting(true);
    try {
      await festivalApi.createFestival({
        name: addName.trim(),
        country_code: addCountry,
        region: addRegion.trim() || undefined,
        category_group: addCategoryGroup,
        description: addDescription.trim() || undefined,
        assigned_leader_id: isManager ? addLeaderId : user?.id,
        initial_year: addYear,
        start_date: addStartDate,
        end_date: addEndDate || addStartDate,
        date_status: addDateStatus,
      });

      setIsAddOpen(false);
      resetAddForm();
      loadFestivals();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create festival.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const resetAddForm = () => {
    setAddName('');
    setAddCountry('IN');
    setAddRegion('');
    setAddDescription('');
    setAddCategoryGroup('RELIGIOUS');
    setAddStartDate('');
    setAddEndDate('');
    setAddDateStatus('ESTIMATED');
    setFormError(null);
  };

  // Preview automatic suggestions
  const handleLoadSuggestions = async () => {
    setSugLoading(true);
    setSugSuccessMsg(null);
    try {
      const sugs = await festivalApi.getFestivalSuggestions(sugCountry, sugYear);
      setSuggestions(sugs);
      setSelectedSugSlugs(sugs.map((s) => s.slug));
    } catch (err: any) {
      alert(err.message || 'Failed to fetch suggestions.');
    } finally {
      setSugLoading(false);
    }
  };

  const handleApplySuggestions = async () => {
    if (selectedSugSlugs.length === 0) {
      alert('Please select at least one festival to apply.');
      return;
    }
    setSugApplying(true);
    try {
      const res = await festivalApi.applyFestivalSuggestions(sugCountry, sugYear, selectedSugSlugs);
      setSugSuccessMsg(`Applied successfully! Created: ${res.created_festivals_count}, Added Editions: ${res.added_year_editions_count}`);
      loadFestivals();
    } catch (err: any) {
      alert(err.message || 'Failed to apply suggestions.');
    } finally {
      setSugApplying(false);
    }
  };

  // Approval action
  const handleOpenApproval = (fest: Festival) => {
    setSelectedFestivalForApproval(fest);
    setApprovalDecision('APPROVED');
    setApprovalNotes('');
    setIsApproveOpen(true);
  };

  const handleApproveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFestivalForApproval || !selectedFestivalForApproval.upcoming_edition_year) return;
    setApprovalLoading(true);
    try {
      await festivalApi.approveFestivalYearDate(
        selectedFestivalForApproval.id,
        selectedFestivalForApproval.upcoming_edition_year,
        approvalDecision,
        approvalNotes || undefined
      );
      setIsApproveOpen(false);
      loadFestivals();
    } catch (err: any) {
      alert(err.message || 'Approval action failed.');
    } finally {
      setApprovalLoading(false);
    }
  };

  const filteredFestivals = festivals.filter((f) => {
    if (statusFilter === 'ALL') return true;
    if (statusFilter === 'PENDING') return f.approval_status === 'PENDING';
    if (statusFilter === 'VERIFIED') return f.date_status === 'VERIFIED' || f.date_status === 'CONFIRMED';
    if (statusFilter === 'ESTIMATED') return f.date_status === 'ESTIMATED';
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-2 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 text-indigo-400">
              <Sparkles className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-bold text-white tracking-tight">Festival SEO Management</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Country-level multi-year event planning, YoY Search Console metrics, and preparation workflow.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Link
            to="/festivals/tasks"
            className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            <CheckSquare className="w-4 h-4 text-emerald-400" />
            <span>Preparation Board</span>
            {overdueCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                {overdueCount}
              </span>
            )}
          </Link>

          {isManager && (
            <>
              <button
                onClick={() => {
                  setIsSuggestionsOpen(true);
                  handleLoadSuggestions();
                }}
                className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 transition-colors"
              >
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span>Auto Suggestions</span>
              </button>

              <button
                onClick={() => {
                  resetAddForm();
                  setIsAddOpen(true);
                }}
                className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Add Festival</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Overview StatCards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg shadow-black/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Festivals</span>
            <span className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Globe className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-white mt-2">{totalCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Across 6 supported countries</div>
        </div>

        <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg shadow-black/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Upcoming (60d)</span>
            <span className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400">
              <Calendar className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-purple-300 mt-2">{upcomingCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Approaching active season</div>
        </div>

        <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg shadow-black/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Requires Approval</span>
            <span className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400">
              <Clock className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-amber-300 mt-2">{pendingApprovalCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">
            {isManager ? 'Pending manager confirmation' : 'Awaiting review'}
          </div>
        </div>

        <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg shadow-black/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Tasks</span>
            <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
              <CheckSquare className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-emerald-300 mt-2">{activeTaskCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">SEO content & technical tasks</div>
        </div>

        <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg shadow-black/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Overdue Tasks</span>
            <span className={`p-1.5 rounded-lg ${overdueCount > 0 ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-800 text-slate-500'}`}>
              <AlertCircle className="w-4 h-4" />
            </span>
          </div>
          <div className={`text-2xl font-bold mt-2 ${overdueCount > 0 ? 'text-rose-400' : 'text-slate-300'}`}>
            {overdueCount}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {overdueCount > 0 ? 'Requires immediate action' : 'All tasks on schedule'}
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 space-y-4">
        {/* Country Quick Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 pb-2 border-b border-slate-800/80">
          <span className="text-xs font-semibold text-slate-400 mr-2 flex items-center space-x-1">
            <Globe className="w-3.5 h-3.5" />
            <span>Country:</span>
          </span>
          {[
            { code: 'ALL', name: 'All Countries', flag: '🌐' },
            { code: 'IN', name: 'India', flag: '🇮🇳' },
            { code: 'US', name: 'USA', flag: '🇺🇸' },
            { code: 'GB', name: 'UK', flag: '🇬🇧' },
            { code: 'CA', name: 'Canada', flag: '🇨🇦' },
            { code: 'AU', name: 'Australia', flag: '🇦🇺' },
            { code: 'AE', name: 'UAE', flag: '🇦🇪' },
          ].map((c) => (
            <button
              key={c.code}
              onClick={() => setCountryFilter(c.code)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center space-x-1.5 ${
                countryFilter === c.code
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'bg-slate-800/70 hover:bg-slate-800 text-slate-300 border border-slate-700/60'
              }`}
            >
              <span>{c.flag}</span>
              <span>{c.name}</span>
            </button>
          ))}
        </div>

        {/* Detailed Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search festival or region..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>

          {/* Year Filter */}
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400 font-medium shrink-0">Year:</span>
            <select
              value={yearFilter}
              onChange={(e) => setYearFilter(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              {[2024, 2025, 2026, 2027, 2028].map((y) => (
                <option key={y} value={y}>
                  Edition {y}
                </option>
              ))}
            </select>
          </div>

          {/* Leader Filter (Manager Only) */}
          {isManager ? (
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-400 font-medium shrink-0">Leader:</span>
              <select
                value={leaderFilter || ''}
                onChange={(e) => setLeaderFilter(e.target.value ? Number(e.target.value) : undefined)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Team Leaders</option>
                {leaders.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.full_name}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div className="flex items-center space-x-2 text-xs text-slate-400 px-3 py-2 bg-slate-950 rounded-xl border border-slate-800">
              <User className="w-3.5 h-3.5 text-emerald-400" />
              <span>Assigned to: {user?.full_name}</span>
            </div>
          )}

          {/* Status Filter */}
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400 font-medium shrink-0">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending Approval</option>
              <option value="VERIFIED">Verified Dates</option>
              <option value="ESTIMATED">Estimated Dates</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Festival Cards / Calendar Interface */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-56 bg-slate-900/60 rounded-2xl animate-pulse border border-slate-800" />
          ))}
        </div>
      ) : error ? (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-6 text-center">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto mb-2" />
          <h3 className="text-sm font-bold text-white">Error Loading Festivals</h3>
          <p className="text-xs text-slate-400 mt-1">{error}</p>
          <button
            onClick={loadFestivals}
            className="mt-4 px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-colors"
          >
            Retry
          </button>
        </div>
      ) : filteredFestivals.length === 0 ? (
        <div className="bg-slate-900/90 rounded-2xl p-12 border border-slate-800 text-center">
          <Sparkles className="w-10 h-10 text-slate-500 mx-auto mb-3" />
          <h3 className="text-base font-bold text-white">No Festivals Found</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
            No festivals match your current filter settings for {yearFilter}. You can add a festival manually or generate suggestions.
          </p>
          {isManager && (
            <div className="flex justify-center gap-3 mt-5">
              <button
                onClick={() => {
                  setIsSuggestionsOpen(true);
                  handleLoadSuggestions();
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 transition-colors"
              >
                Auto-Suggest Festivals
              </button>
              <button
                onClick={() => {
                  resetAddForm();
                  setIsAddOpen(true);
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
              >
                Create Custom Festival
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredFestivals.map((fest) => {
            const countryName = COUNTRY_NAMES[fest.country_code] || fest.country_code;
            const flag = COUNTRY_FLAGS[fest.country_code] || '🌐';

            // Calculate days remaining
            let daysRemaining: number | null = null;
            if (fest.upcoming_start_date) {
              const today = new Date();
              today.setHours(0, 0, 0, 0);
              const festDate = new Date(fest.upcoming_start_date);
              daysRemaining = Math.ceil((festDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
            }

            return (
              <div
                key={fest.id}
                className="bg-slate-900/90 rounded-2xl p-5 border border-slate-800 shadow-xl shadow-black/20 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-base">{flag}</span>
                        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                          {countryName} {fest.region ? `• ${fest.region}` : ''}
                        </span>
                      </div>
                      <Link
                        to={`/festivals/${fest.id}`}
                        className="text-lg font-bold text-white hover:text-indigo-400 transition-colors tracking-tight mt-1 block"
                      >
                        {fest.name}
                      </Link>
                    </div>

                    {/* Verification Badge */}
                    <div>
                      {fest.date_status === 'VERIFIED' || fest.date_status === 'CONFIRMED' ? (
                        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          <CheckCircle className="w-3 h-3" />
                          <span>VERIFIED</span>
                        </span>
                      ) : fest.date_status === 'ESTIMATED' ? (
                        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                          <Clock className="w-3 h-3" />
                          <span>ESTIMATED</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                          <AlertTriangle className="w-3 h-3" />
                          <span>UNVERIFIED</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Dates & Countdown */}
                  <div className="mt-4 p-3 rounded-xl bg-slate-950/80 border border-slate-800/80">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 font-medium">Edition:</span>
                      <span className="text-slate-200 font-bold">
                        {fest.upcoming_edition_year ? `${fest.upcoming_edition_year}` : 'No edition'}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs mt-1.5">
                      <span className="text-slate-400 font-medium">Dates:</span>
                      <span className="text-white font-semibold">
                        {fest.upcoming_start_date ? (
                          <>
                            {fest.upcoming_start_date}
                            {fest.upcoming_end_date && fest.upcoming_end_date !== fest.upcoming_start_date
                              ? ` - ${fest.upcoming_end_date}`
                              : ''}
                          </>
                        ) : (
                          'Dates TBD'
                        )}
                      </span>
                    </div>

                    {daysRemaining !== null && (
                      <div className="flex items-center justify-between text-xs mt-1.5 pt-1.5 border-t border-slate-800/60">
                        <span className="text-slate-400 font-medium">Timeline:</span>
                        <span
                          className={`font-semibold ${
                            daysRemaining < 0
                              ? 'text-slate-500'
                              : daysRemaining === 0
                              ? 'text-emerald-400 font-bold'
                              : daysRemaining <= 30
                              ? 'text-amber-400 font-bold'
                              : 'text-indigo-400'
                          }`}
                        >
                          {daysRemaining < 0
                            ? `${Math.abs(daysRemaining)} days ago`
                            : daysRemaining === 0
                            ? 'Today!'
                            : `In ${daysRemaining} days`}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Metadata Row: Leader & Landing Pages */}
                  <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                    <div className="flex items-center space-x-1.5">
                      <User className="w-3.5 h-3.5 text-indigo-400" />
                      <span className="truncate max-w-[140px] text-slate-300 font-medium">
                        {fest.assigned_leader_name || 'Unassigned'}
                      </span>
                    </div>

                    <div className="flex items-center space-x-1">
                      <Layers className="w-3.5 h-3.5 text-slate-400" />
                      <span className="text-slate-300 font-medium">{fest.page_count} URLs</span>
                    </div>
                  </div>

                  {/* Task Completion Progress */}
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                      <span>Prep Tasks</span>
                      <span className="font-semibold text-slate-300">{fest.task_completion_pct}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(100, fest.task_completion_pct)}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Footer Actions */}
                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                  <div className="flex items-center space-x-1.5">
                    {fest.approval_status === 'APPROVED' ? (
                      <span className="inline-flex items-center space-x-1 text-[10px] font-semibold text-emerald-400">
                        <Check className="w-3 h-3" />
                        <span>Manager Approved</span>
                      </span>
                    ) : fest.approval_status === 'REJECTED' ? (
                      <span className="inline-flex items-center space-x-1 text-[10px] font-semibold text-rose-400">
                        <X className="w-3 h-3" />
                        <span>Rejected</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center space-x-1 text-[10px] font-semibold text-amber-400 animate-pulse">
                        <Clock className="w-3 h-3" />
                        <span>Needs Approval</span>
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-1.5">
                    {isManager && fest.approval_status === 'PENDING' && (
                      <button
                        onClick={() => handleOpenApproval(fest)}
                        className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 transition-colors"
                      >
                        Review
                      </button>
                    )}

                    <Link
                      to={`/festivals/${fest.id}`}
                      className="inline-flex items-center space-x-1 px-3 py-1 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                    >
                      <span>Details & YoY</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ================= MODAL: ADD FESTIVAL (Manager Only) ================= */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl p-6 overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <span className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400">
                  <Plus className="w-4 h-4" />
                </span>
                <h3 className="text-base font-bold text-white">Create Custom Festival</h3>
              </div>
              <button
                onClick={() => setIsAddOpen(false)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleAddSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Festival Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Diwali, Thanksgiving, Holi"
                  value={addName}
                  onChange={(e) => setAddName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Country *</label>
                  <select
                    value={addCountry}
                    onChange={(e) => setAddCountry(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="IN">India (IN)</option>
                    <option value="US">USA (US)</option>
                    <option value="GB">UK (GB)</option>
                    <option value="CA">Canada (CA)</option>
                    <option value="AU">Australia (AU)</option>
                    <option value="AE">UAE (AE)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Region / State</label>
                  <input
                    type="text"
                    placeholder="e.g. Nationwide, North, Gujarat"
                    value={addRegion}
                    onChange={(e) => setAddRegion(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Category Group</label>
                  <select
                    value={addCategoryGroup}
                    onChange={(e) => setAddCategoryGroup(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="RELIGIOUS">Religious Festival</option>
                    <option value="NATIONAL">National Holiday</option>
                    <option value="SEASONAL">Seasonal Celebration</option>
                    <option value="CULTURAL">Cultural Event</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Assigned Team Leader *</label>
                  <select
                    value={addLeaderId}
                    onChange={(e) => setAddLeaderId(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {leaders.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.full_name} ({l.role})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800">
                <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider block mb-2">
                  Initial Year Edition Dates
                </span>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Year</label>
                    <input
                      type="number"
                      value={addYear}
                      onChange={(e) => setAddYear(Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Start Date *</label>
                    <input
                      type="date"
                      required
                      value={addStartDate}
                      onChange={(e) => {
                        setAddStartDate(e.target.value);
                        if (!addEndDate) setAddEndDate(e.target.value);
                      }}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">End Date</label>
                    <input
                      type="date"
                      value={addEndDate}
                      onChange={(e) => setAddEndDate(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div className="mt-3">
                  <label className="block text-xs font-medium text-slate-300 mb-1">Date Verification Status</label>
                  <select
                    value={addDateStatus}
                    onChange={(e) => setAddDateStatus(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="ESTIMATED">ESTIMATED (Astronomical / Lunar cycle approximation)</option>
                    <option value="UNVERIFIED">UNVERIFIED (Requires calendar confirmation)</option>
                    <option value="VERIFIED">VERIFIED (Confirmed by official calendar or gazette)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="SEO themes, key templates, or event significance..."
                  value={addDescription}
                  onChange={(e) => setAddDescription(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-50"
                >
                  {formSubmitting ? 'Creating...' : 'Create Festival'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: AUTOMATIC SUGGESTIONS (Manager Only) ================= */}
      {isSuggestionsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl p-6 overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <span className="p-2 rounded-xl bg-purple-500/20 text-purple-400">
                  <Sparkles className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-white">Automatic Festival Suggestions</h3>
                  <p className="text-xs text-slate-400">
                    Preview and batch-apply suggested festivals computed via national calendars and lunar algorithms.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsSuggestionsOpen(false)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Country & Year Selector Toolbar */}
            <div className="mt-4 p-3 bg-slate-950 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-1.5">
                  <span className="text-xs text-slate-400 font-medium">Country:</span>
                  <select
                    value={sugCountry}
                    onChange={(e) => {
                      setSugCountry(e.target.value);
                    }}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-white"
                  >
                    <option value="IN">🇮🇳 India</option>
                    <option value="US">🇺🇸 USA</option>
                    <option value="GB">🇬🇧 UK</option>
                    <option value="CA">🇨🇦 Canada</option>
                    <option value="AU">🇦🇺 Australia</option>
                    <option value="AE">🇦🇪 UAE</option>
                  </select>
                </div>

                <div className="flex items-center space-x-1.5">
                  <span className="text-xs text-slate-400 font-medium">Year:</span>
                  <select
                    value={sugYear}
                    onChange={(e) => {
                      setSugYear(Number(e.target.value));
                    }}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-white"
                  >
                    {[2024, 2025, 2026, 2027].map((y) => (
                      <option key={y} value={y}>
                        {y}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                onClick={handleLoadSuggestions}
                disabled={sugLoading}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${sugLoading ? 'animate-spin' : ''}`} />
                <span>Fetch Suggestions</span>
              </button>
            </div>

            {sugSuccessMsg && (
              <div className="mt-3 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300 flex items-center space-x-2">
                <CheckCircle className="w-4 h-4 shrink-0" />
                <span>{sugSuccessMsg}</span>
              </div>
            )}

            {/* Suggestions Table / List */}
            <div className="mt-4">
              {sugLoading ? (
                <div className="p-8 text-center text-slate-400 text-xs">Computing astronomical and calendar suggestions...</div>
              ) : suggestions.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs">No suggestions found for {sugCountry} {sugYear}.</div>
              ) : (
                <div className="border border-slate-800 rounded-xl overflow-hidden">
                  <div className="p-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between text-xs">
                    <label className="flex items-center space-x-2 text-slate-300 font-medium cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedSugSlugs.length === suggestions.length}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedSugSlugs(suggestions.map((s) => s.slug));
                          } else {
                            setSelectedSugSlugs([]);
                          }
                        }}
                        className="rounded border-slate-700 text-indigo-600 focus:ring-0"
                      />
                      <span>Select All ({suggestions.length})</span>
                    </label>

                    <span className="text-slate-400">{selectedSugSlugs.length} selected</span>
                  </div>

                  <div className="divide-y divide-slate-800/60 max-h-72 overflow-y-auto">
                    {suggestions.map((s) => {
                      const isSelected = selectedSugSlugs.includes(s.slug);
                      return (
                        <div
                          key={s.slug}
                          className={`p-3 flex items-center justify-between gap-3 text-xs transition-colors ${
                            isSelected ? 'bg-indigo-950/20' : 'hover:bg-slate-800/40'
                          }`}
                        >
                          <label className="flex items-start space-x-2.5 cursor-pointer flex-1 min-w-0">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedSugSlugs([...selectedSugSlugs, s.slug]);
                                } else {
                                  setSelectedSugSlugs(selectedSugSlugs.filter((slug) => slug !== s.slug));
                                }
                              }}
                              className="mt-0.5 rounded border-slate-700 text-indigo-600 focus:ring-0"
                            />
                            <div className="min-w-0">
                              <div className="font-bold text-white flex items-center space-x-2">
                                <span>{s.name}</span>
                                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700">
                                  {s.calculation_type}
                                </span>
                              </div>
                              <div className="text-slate-400 text-[11px] mt-0.5">
                                Dates: <span className="text-slate-200 font-medium">{s.start_date} to {s.end_date}</span>
                                {' • '}
                                Prep: <span className="text-indigo-300">{s.prep_start_date}</span>
                              </div>
                            </div>
                          </label>

                          <div className="shrink-0 text-right">
                            {s.date_status === 'VERIFIED' || s.date_status === 'CONFIRMED' ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                                VERIFIED
                              </span>
                            ) : s.date_status === 'ESTIMATED' ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                                ESTIMATED
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                                UNVERIFIED
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-5 pt-4 border-t border-slate-800 flex items-center justify-between">
              <span className="text-[11px] text-amber-400 flex items-center space-x-1">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                <span>Applied suggestions start with approval_status='PENDING'</span>
              </span>

              <div className="flex space-x-2">
                <button
                  type="button"
                  onClick={() => setIsSuggestionsOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={handleApplySuggestions}
                  disabled={sugApplying || selectedSugSlugs.length === 0}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white transition-colors disabled:opacity-50"
                >
                  {sugApplying ? 'Applying...' : `Apply Selected (${selectedSugSlugs.length})`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================= MODAL: APPROVE / REJECT DATES (Manager Only) ================= */}
      {isApproveOpen && selectedFestivalForApproval && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <span className="p-2 rounded-xl bg-amber-500/20 text-amber-400">
                  <Shield className="w-4 h-4" />
                </span>
                <h3 className="text-base font-bold text-white">Manager Date Approval</h3>
              </div>
              <button
                onClick={() => setIsApproveOpen(false)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs">
              <div className="font-bold text-white text-sm">{selectedFestivalForApproval.name}</div>
              <div className="text-slate-400 mt-1">
                Edition {selectedFestivalForApproval.upcoming_edition_year}:{' '}
                <span className="text-slate-200 font-medium">
                  {selectedFestivalForApproval.upcoming_start_date} to {selectedFestivalForApproval.upcoming_end_date}
                </span>
              </div>
              <div className="text-slate-400 mt-0.5">
                Current Date Status:{' '}
                <span className="text-amber-400 font-semibold">{selectedFestivalForApproval.date_status}</span>
              </div>
            </div>

            <form onSubmit={handleApproveSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Decision</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setApprovalDecision('APPROVED')}
                    className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all flex items-center justify-center space-x-1.5 ${
                      approvalDecision === 'APPROVED'
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50 shadow-md shadow-emerald-500/10'
                        : 'bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700'
                    }`}
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Approve Dates</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setApprovalDecision('REJECTED')}
                    className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all flex items-center justify-center space-x-1.5 ${
                      approvalDecision === 'REJECTED'
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/50 shadow-md shadow-rose-500/10'
                        : 'bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700'
                    }`}
                  >
                    <X className="w-3.5 h-3.5" />
                    <span>Reject Dates</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Approval Notes (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="e.g. Verified with Government official gazette calendar."
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsApproveOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={approvalLoading}
                  className={`px-5 py-2 rounded-xl text-xs font-semibold text-white transition-colors disabled:opacity-50 ${
                    approvalDecision === 'APPROVED'
                      ? 'bg-emerald-600 hover:bg-emerald-500'
                      : 'bg-rose-600 hover:bg-rose-500'
                  }`}
                >
                  {approvalLoading ? 'Saving...' : `Confirm ${approvalDecision}`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default FestivalDashboardPage;
