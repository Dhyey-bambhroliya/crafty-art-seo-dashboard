import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText, Search, ArrowUpDown, ExternalLink, ChevronRight,
  TrendingDown, TrendingUp, Minus, Filter, User, RefreshCw,
  Calendar, Info, Copy, Check, ChevronLeft, ArrowUpRight, ArrowDownRight,
  Sparkles, Globe, Layers, AlertCircle, ShieldAlert
} from 'lucide-react';
import { api } from '../services/api';
import {
  Category, User as UserType, LandingPageTrafficItem,
  LandingPageTrafficSummary
} from '../types';
import { useAuth } from '../context/AuthContext';

export const PagesMonitoringPage: React.FC = () => {
  const { user, role } = useAuth();
  const isManager = role === 'MANAGER';

  const [items, setItems] = useState<LandingPageTrafficItem[]>([]);
  const [summary, setSummary] = useState<LandingPageTrafficSummary | null>(null);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  const [categories, setCategories] = useState<Category[]>([]);
  const [leaders, setLeaders] = useState<UserType[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Filters & Sorting
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<number | undefined>(undefined);
  const [leaderFilter, setLeaderFilter] = useState<number | undefined>(
    !isManager && user ? user.id : undefined
  );
  const [sortBy, setSortBy] = useState<string>('clicks_28d_desc');
  const [comparisonPeriod, setComparisonPeriod] = useState<'7d' | '28d'>('28d');

  // UI helpers
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);
  const [showGa4Modal, setShowGa4Modal] = useState(false);

  const loadData = async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const [trafficRes, catsRes, leadersRes] = await Promise.all([
        api.getLandingPageTraffic({
          category_id: categoryFilter,
          leader_id: leaderFilter,
          search: search.trim() || undefined,
          sort_by: sortBy,
          page,
          page_size: pageSize,
        }),
        api.getCategories(),
        isManager ? api.getLeaders() : Promise.resolve([]),
      ]);

      setItems(trafficRes.items);
      setSummary(trafficRes.summary);
      setTotalItems(trafficRes.total_items);
      setTotalPages(trafficRes.total_pages);
      setCategories(catsRes);
      if (isManager) setLeaders(leadersRes);
    } catch (err) {
      console.error('Failed to load landing page traffic data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [categoryFilter, leaderFilter, sortBy, page, pageSize]);

  // Handle search with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
      loadData();
    }, 350);
    return () => clearTimeout(timer);
  }, [search]);

  const handleCopy = (url: string) => {
    navigator.clipboard.writeText(url);
    setCopiedUrl(url);
    setTimeout(() => setCopiedUrl(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Landing Page Traffic Monitoring
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Multi-window traffic ingestion (24h, 3d, 7d, 28d) and performance comparisons across Crafty Art landing pages.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2.5 self-start md:self-auto">
          {summary?.latest_data_date && (
            <div className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-[11px] text-slate-300 flex items-center space-x-1.5">
              <Calendar className="w-3.5 h-3.5 text-indigo-400" />
              <span>GSC Data: <strong className="text-white font-medium">{summary.latest_data_date}</strong></span>
            </div>
          )}

          <button
            onClick={() => loadData(true)}
            disabled={refreshing || loading}
            className="px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-200 font-medium transition flex items-center space-x-1.5 disabled:opacity-50"
            title="Refresh traffic metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-indigo-400 ${refreshing ? 'animate-spin' : ''}`} />
            <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg shadow-black/20">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Monitored URLs</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {summary?.total_pages_monitored.toLocaleString() || 0}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 truncate">
            Across active Crafty Art categories
          </div>
        </div>

        <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg shadow-black/20">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">7-Day Clicks (GSC)</span>
            <Globe className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {summary?.total_clicks_7d.toLocaleString() || 0}
          </div>
          <div className="text-[11px] text-emerald-400 mt-1 flex items-center space-x-1">
            <ArrowUpRight className="w-3.5 h-3.5" />
            <span>{summary?.reporting_range_7d || 'Past 7 days'}</span>
          </div>
        </div>

        <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg shadow-black/20">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">28-Day Clicks (GSC)</span>
            <TrendingUp className="w-4 h-4 text-violet-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {summary?.total_clicks_28d.toLocaleString() || 0}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {summary?.total_impressions_28d.toLocaleString() || 0} impressions
          </div>
        </div>

        <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg shadow-black/20">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Avg Position (28d)</span>
            <ArrowUpDown className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {summary?.avg_position_28d ? summary.avg_position_28d.toFixed(1) : '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            Impression-weighted ranking
          </div>
        </div>

        <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-lg shadow-black/20">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Rolling 24h Traffic</span>
            <button
              onClick={() => setShowGa4Modal(true)}
              className="text-amber-400 hover:text-amber-300"
              title="Learn about GA4 24h integration"
            >
              <Info className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30 uppercase tracking-wide">
              GA4 Required
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1.5 flex items-center justify-between">
            <span>Latest Day Clicks:</span>
            <strong className="text-slate-200">
              {items.reduce((acc, curr) => acc + curr.latest_gsc_day_clicks, 0).toLocaleString()}
            </strong>
          </div>
        </div>
      </div>

      {/* Filter and Control Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/90 p-3 rounded-2xl border border-slate-800 shadow-lg shadow-black/10">
        {/* Search */}
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search landing page URL..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-950 text-slate-200 text-xs border border-slate-800 focus:outline-none focus:border-indigo-500 placeholder-slate-600 font-mono"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Comparison Mode Toggle */}
          <div className="flex items-center p-1 bg-slate-950 rounded-xl border border-slate-800 text-xs">
            <button
              type="button"
              onClick={() => setComparisonPeriod('7d')}
              className={`px-2.5 py-1 rounded-lg font-medium transition ${
                comparisonPeriod === '7d'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              7-Day Growth
            </button>
            <button
              type="button"
              onClick={() => setComparisonPeriod('28d')}
              className={`px-2.5 py-1 rounded-lg font-medium transition ${
                comparisonPeriod === '28d'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              28-Day Growth
            </button>
          </div>

          {/* Category Filter */}
          <select
            value={categoryFilter || ''}
            onChange={(e) => {
              setCategoryFilter(e.target.value ? Number(e.target.value) : undefined);
              setPage(1);
            }}
            className="bg-slate-950 text-slate-200 text-xs px-3 py-2 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          {/* Leader Filter (Managers Only) */}
          {isManager && (
            <select
              value={leaderFilter || ''}
              onChange={(e) => {
                setLeaderFilter(e.target.value ? Number(e.target.value) : undefined);
                setPage(1);
              }}
              className="bg-slate-950 text-slate-200 text-xs px-3 py-2 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Team Leaders</option>
              {leaders.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.full_name}
                </option>
              ))}
            </select>
          )}

          {/* Sort By Dropdown */}
          <div className="flex items-center space-x-1.5 bg-slate-950 px-3 py-2 rounded-xl border border-slate-800">
            <ArrowUpDown className="w-3.5 h-3.5 text-indigo-400" />
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
              className="bg-transparent text-slate-200 text-xs focus:outline-none font-medium"
            >
              <option value="clicks_28d_desc">Highest 28-Day Traffic</option>
              <option value="clicks_28d_asc">Lowest 28-Day Traffic</option>
              <option value="clicks_7d_desc">Highest 7-Day Traffic</option>
              <option value="clicks_3d_desc">Highest 3-Day Traffic</option>
              <option value="growth_desc">Largest Traffic Growth %</option>
              <option value="drop_desc">Largest Traffic Drop %</option>
              <option value="url_asc">Landing Page URL (A-Z)</option>
            </select>
          </div>

          {/* Page Size */}
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
            className="bg-slate-950 text-slate-200 text-xs px-2.5 py-2 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500"
            title="Rows per page"
          >
            <option value={10}>10 / page</option>
            <option value={25}>25 / page</option>
            <option value={50}>50 / page</option>
            <option value={100}>100 / page</option>
          </select>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl shadow-black/20">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/70 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-5 min-w-[240px]">Landing Page URL</th>
                <th className="py-3.5 px-3 min-w-[130px]">Category</th>
                <th className="py-3.5 px-3 min-w-[120px]">Team Leader</th>
                <th className="py-3.5 px-3 min-w-[130px]">
                  <div className="flex items-center space-x-1">
                    <span>Last 24 Hours</span>
                    <button onClick={() => setShowGa4Modal(true)} title="Requires GA4 for rolling 24h">
                      <Info className="w-3 h-3 text-amber-400" />
                    </button>
                  </div>
                </th>
                <th className="py-3.5 px-3 min-w-[110px]" title={summary?.reporting_range_3d || 'Last 3 complete days'}>
                  Last 3 Days
                </th>
                <th className="py-3.5 px-3 min-w-[110px]" title={summary?.reporting_range_7d || 'Last 7 complete days'}>
                  Last 7 Days
                </th>
                <th className="py-3.5 px-3 min-w-[130px]" title={summary?.reporting_range_28d || 'Last 28 complete days'}>
                  Last 28 Days
                </th>
                <th className="py-3.5 px-3 min-w-[130px]">
                  {comparisonPeriod === '7d' ? '7d Growth / Drop' : '28d Growth / Drop'}
                </th>
                <th className="py-3.5 px-4 min-w-[110px]">Last Updated</th>
                <th className="py-3.5 px-4 text-right">Details</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {items.map((item) => {
                const comp = comparisonPeriod === '7d' ? item.comparison_7d : item.comparison_28d;
                const isGrowth = comp.status === 'GROWTH';
                const isDecline = comp.status === 'DECLINE';

                return (
                  <tr key={item.id} className="hover:bg-slate-800/30 transition-colors">
                    {/* Landing Page URL */}
                    <td className="py-3.5 px-5 max-w-xs">
                      <div className="flex items-center space-x-2">
                        <Link
                          to={`/pages/${item.id}`}
                          className="font-mono text-slate-200 hover:text-indigo-400 truncate block font-medium transition-colors"
                          title={item.full_url}
                        >
                          {item.full_url}
                        </Link>
                        <div className="flex items-center space-x-1 shrink-0">
                          <button
                            type="button"
                            onClick={() => handleCopy(item.full_url)}
                            className="p-1 rounded text-slate-500 hover:text-slate-300 transition"
                            title="Copy URL"
                          >
                            {copiedUrl === item.full_url ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                          <a
                            href={item.full_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1 rounded text-slate-500 hover:text-slate-300 transition"
                            title="Open in new tab"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </div>
                      </div>
                    </td>

                    {/* Category */}
                    <td className="py-3.5 px-3">
                      <span className="px-2 py-0.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-200 font-medium text-[11px] truncate block max-w-[130px]">
                        {item.category_name}
                      </span>
                    </td>

                    {/* Team Leader */}
                    <td className="py-3.5 px-3 text-slate-300 font-medium text-[11px] truncate max-w-[120px]">
                      {item.leader_name}
                    </td>

                    {/* Last 24 Hours */}
                    <td className="py-3.5 px-3">
                      <div>
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          GA4 Required
                        </span>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          Latest GSC: <strong className="text-white font-medium">{item.latest_gsc_day_clicks} clicks</strong>
                        </p>
                      </div>
                    </td>

                    {/* Last 3 Days */}
                    <td className="py-3.5 px-3">
                      <div>
                        <span className="font-bold text-white text-[13px]">
                          {item.traffic_3d.clicks.toLocaleString()}
                        </span>
                        <span className="text-[10px] text-slate-400 ml-1">clicks</span>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {item.traffic_3d.impressions.toLocaleString()} imp • {item.traffic_3d.ctr}%
                        </p>
                      </div>
                    </td>

                    {/* Last 7 Days */}
                    <td className="py-3.5 px-3">
                      <div>
                        <span className="font-bold text-white text-[13px]">
                          {item.traffic_7d.clicks.toLocaleString()}
                        </span>
                        <span className="text-[10px] text-slate-400 ml-1">clicks</span>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {item.traffic_7d.impressions.toLocaleString()} imp • {item.traffic_7d.ctr}%
                        </p>
                      </div>
                    </td>

                    {/* Last 28 Days */}
                    <td className="py-3.5 px-3">
                      <div>
                        <span className="font-bold text-white text-[13px]">
                          {item.traffic_28d.clicks.toLocaleString()}
                        </span>
                        <span className="text-[10px] text-slate-400 ml-1">clicks</span>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {item.traffic_28d.impressions.toLocaleString()} imp • Pos: {item.traffic_28d.position || '—'}
                        </p>
                      </div>
                    </td>

                    {/* Growth / Drop Percentage */}
                    <td className="py-3.5 px-3">
                      <div className="flex flex-col space-y-0.5">
                        <span
                          className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-bold w-max ${
                            isGrowth
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                              : isDecline
                              ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {isGrowth && <ArrowUpRight className="w-3.5 h-3.5 shrink-0" />}
                          {isDecline && <ArrowDownRight className="w-3.5 h-3.5 shrink-0" />}
                          {!isGrowth && !isDecline && <Minus className="w-3.5 h-3.5 shrink-0" />}
                          <span>{comp.click_diff > 0 ? `+${comp.click_diff}` : comp.click_diff} ({comp.pct_change > 0 ? `+${comp.pct_change}` : comp.pct_change}%)</span>
                        </span>
                        <span className="text-[9px] text-slate-400">
                          prev: {comp.previous_clicks.toLocaleString()} clicks
                        </span>
                      </div>
                    </td>

                    {/* Last Updated */}
                    <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                      {summary?.latest_data_date ? (
                        <span>{summary.latest_data_date}</span>
                      ) : (
                        <span>Pending sync</span>
                      )}
                    </td>

                    {/* Details Action */}
                    <td className="py-3.5 px-4 text-right">
                      <Link
                        to={`/pages/${item.id}`}
                        className="inline-flex items-center space-x-1 text-xs text-indigo-400 hover:text-indigo-300 font-semibold px-2 py-1 rounded-lg hover:bg-indigo-500/10 transition"
                      >
                        <span>Details</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                );
              })}

              {items.length === 0 && !loading && (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <FileText className="w-8 h-8 text-slate-600" />
                      <p className="font-semibold text-slate-300">No landing pages match your criteria.</p>
                      <p className="text-xs text-slate-500 max-w-sm">
                        Try clearing search terms or map landing page URLs in the Categories section.
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {totalItems > 0 && (
          <div className="p-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-950/40 text-xs text-slate-400">
            <div>
              Showing <strong className="text-white font-medium">{(page - 1) * pageSize + 1}</strong> to{' '}
              <strong className="text-white font-medium">{Math.min(page * pageSize, totalItems)}</strong> of{' '}
              <strong className="text-white font-medium">{totalItems}</strong> landing pages
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                disabled={page <= 1}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium disabled:opacity-40 disabled:cursor-not-allowed transition flex items-center space-x-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>

              <span className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 font-mono">
                Page {page} of {totalPages || 1}
              </span>

              <button
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                disabled={page >= totalPages}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium disabled:opacity-40 disabled:cursor-not-allowed transition flex items-center space-x-1"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* GA4 24h Traffic Architecture Info Modal */}
      {showGa4Modal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 rounded-2xl border border-slate-800 max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Google Analytics 4 (GA4) Architecture</h3>
                  <p className="text-xs text-slate-400">Real-time rolling 24-hour visitors requirement</p>
                </div>
              </div>
              <button
                onClick={() => setShowGa4Modal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            <div className="text-xs text-slate-300 space-y-3 leading-relaxed">
              <p>
                <strong>Why "GA4 Required"?</strong> Google Search Console (GSC) measures organic search clicks and impressions with an industry-standard <strong>2-to-3-day data latency</strong>. It does not measure real-time website visits or rolling 24-hour sessions.
              </p>
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                <div className="font-semibold text-indigo-400 flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Ready GA4 Integration Architecture</span>
                </div>
                <p className="text-slate-400 text-[11px]">
                  Your dashboard's database is already architected with <code className="text-emerald-400">SystemSetting</code> to store:
                </p>
                <ul className="list-disc list-inside text-[11px] text-slate-400 space-y-1">
                  <li><code className="text-indigo-300">GA4_PROPERTY_ID</code>: Numeric GA4 Property ID</li>
                  <li><code className="text-indigo-300">GA4_CREDENTIALS_JSON</code>: Google Cloud Service Account JSON Key</li>
                  <li><code className="text-indigo-300">GA4_METRIC_TYPE</code>: 'screenPageViews' or 'sessions'</li>
                </ul>
              </div>
              <p className="text-[11px] text-slate-400">
                Whenever you are ready to connect GA4, the backend endpoint will automatically transition from <em>GA4 Required</em> to true rolling 24h page views without requiring any database wipes or schema rebuilds.
              </p>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setShowGa4Modal(false)}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition"
              >
                Understood
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
