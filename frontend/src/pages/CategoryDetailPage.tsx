import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Plus, Trash2, ArrowUpRight, TrendingDown, TrendingUp,
  MousePointer, Eye, Percent, Target, AlertTriangle, AlertCircle,
  ExternalLink, CheckCircle2, ChevronRight, Layers, CheckCircle, XCircle
} from 'lucide-react';
import { StatCard } from '../components/common/StatCard';
import { TrendChart } from '../components/common/TrendChart';
import { StatusBadge } from '../components/common/StatusBadge';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export const CategoryDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const categoryId = Number(id);
  const navigate = useNavigate();
  const { user, role } = useAuth();
  const isManager = role === 'MANAGER';

  const [categoryData, setCategoryData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  // Add Page Modal
  const [isAddPageOpen, setIsAddPageOpen] = useState(false);
  const [addMode, setAddMode] = useState<'bulk' | 'single'>('bulk');
  const [newUrl, setNewUrl] = useState('');
  const [bulkUrlsText, setBulkUrlsText] = useState('');
  const [bulkCheckResult, setBulkCheckResult] = useState<any | null>(null);
  const [urlWarning, setUrlWarning] = useState<string | null>(null);
  const [addError, setAddError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);
  const [addingLoading, setAddingLoading] = useState(false);
  const [validatingBulk, setValidatingBulk] = useState(false);

  const loadCategory = async () => {
    setLoading(true);
    try {
      const data = await api.getCategoryDetails(categoryId);
      setCategoryData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (categoryId) loadCategory();
  }, [categoryId]);

  const parseBulkUrls = (text: string): string[] => {
    return text
      .split(/[\n,]+/)
      .map((u) => u.trim())
      .filter((u) => u.length > 0);
  };

  const handleBulkTextChange = async (text: string) => {
    setBulkUrlsText(text);
    setAddError(null);
    const parsed = parseBulkUrls(text);
    if (parsed.length === 0) {
      setBulkCheckResult(null);
      return;
    }

    setValidatingBulk(true);
    try {
      const res = await api.checkUrlsBulk(categoryId, parsed);
      setBulkCheckResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setValidatingBulk(false);
    }
  };

  const handleUrlChange = async (url: string) => {
    setNewUrl(url);
    setUrlWarning(null);
    if (url.trim().length > 10) {
      try {
        const check = await api.checkUrlDuplicate(categoryId, url);
        if (check.warning_message) {
          setUrlWarning(check.warning_message);
        }
      } catch {}
    }
  };

  const handleAddPageSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddError(null);
    setAddingLoading(true);

    try {
      if (addMode === 'single') {
        await api.addPageToCategory(categoryId, newUrl);
        setSuccessNotice('Page added successfully!');
      } else {
        const parsed = parseBulkUrls(bulkUrlsText);
        if (parsed.length === 0) {
          throw new Error('Please enter at least one URL.');
        }
        const res = await api.addPagesBulk(categoryId, parsed);
        setSuccessNotice(`Successfully added ${res.added_count} page(s) to ${categoryData.name}! ${res.skipped_count > 0 ? `(${res.skipped_count} duplicates skipped)` : ''}`);
      }
      setIsAddPageOpen(false);
      setNewUrl('');
      setBulkUrlsText('');
      setBulkCheckResult(null);
      setUrlWarning(null);
      loadCategory();
      setTimeout(() => setSuccessNotice(null), 5000);
    } catch (err: any) {
      setAddError(err.message || 'Failed to add pages.');
    } finally {
      setAddingLoading(false);
    }
  };

  const handleRemovePage = async (pageId: number, url: string) => {
    if (!window.confirm(`Remove URL '${url}' from this category?`)) return;
    try {
      await api.removePageFromCategory(categoryId, pageId);
      loadCategory();
    } catch (err: any) {
      alert(`Remove error: ${err.message}`);
    }
  };

  const handleReviewAlert = async (alertId: number) => {
    try {
      await api.updateAlertStatus(alertId, 'REVIEWED');
      loadCategory();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDeleteCategory = async () => {
    if (!categoryData) return;
    if (!window.confirm(`Are you sure you want to permanently delete category '${categoryData.name}' and all its mapped page associations?`)) {
      return;
    }
    try {
      await api.deleteCategory(categoryId);
      navigate('/categories');
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  if (loading || !categoryData) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-48 bg-slate-900 rounded" />
        <div className="h-32 bg-slate-900 rounded-2xl" />
        <div className="h-64 bg-slate-900 rounded-2xl" />
      </div>
    );
  }

  const canManage = isManager || Number(categoryData.assigned_leader_id) === Number(user?.id);
  const comp = categoryData.comparison;

  return (
    <div className="space-y-6">
      {/* Back button & Breadcrumb */}
      <div>
        <Link
          to="/categories"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-400 hover:text-white transition-colors mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to All Categories</span>
        </Link>

        {successNotice && (
          <div className="mb-4 p-4 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center space-x-2.5">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{successNotice}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-3">
              <span>{categoryData.name}</span>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {categoryData.status}
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Assigned Leader: <span className="text-indigo-400 font-semibold">{categoryData.leader_name}</span> •{' '}
              {categoryData.page_count} Mapped URLs
            </p>
          </div>

          {canManage && (
            <div className="flex items-center space-x-2 self-start sm:self-auto">
              <button
                onClick={() => {
                  setNewUrl('');
                  setUrlWarning(null);
                  setAddError(null);
                  setIsAddPageOpen(true);
                }}
                className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-all"
              >
                <Plus className="w-4 h-4" />
                <span>Map Page URL</span>
              </button>
              <button
                onClick={handleDeleteCategory}
                className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-rose-500/15 text-slate-300 hover:text-rose-400 border border-slate-700 hover:border-rose-500/30 text-xs font-semibold transition-all"
                title="Delete this category"
              >
                <Trash2 className="w-4 h-4" />
                <span>Delete Category</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* KPI Cards for this Category */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Category Clicks (28d)"
          currentValue={comp.current.clicks}
          previousValue={comp.previous.clicks}
          diff={comp.click_diff}
          pctChange={comp.click_pct_change}
          icon={<MousePointer className="w-4 h-4 text-indigo-400" />}
        />
        <StatCard
          title="Category Impressions (28d)"
          currentValue={comp.current.impressions}
          previousValue={comp.previous.impressions}
          diff={comp.impression_diff}
          pctChange={comp.impression_pct_change}
          icon={<Eye className="w-4 h-4 text-violet-400" />}
        />
        <StatCard
          title="Category CTR"
          currentValue={comp.current.ctr}
          previousValue={comp.previous.ctr}
          diff={comp.ctr_diff}
          suffix="%"
          icon={<Percent className="w-4 h-4 text-emerald-400" />}
        />
        <StatCard
          title="Weighted Avg Position"
          currentValue={comp.current.position}
          previousValue={comp.previous.position}
          diff={comp.position_diff}
          isPosition={true}
          icon={<Target className="w-4 h-4 text-amber-400" />}
        />
      </div>

      {/* Daily Trends Chart */}
      <TrendChart
        data={categoryData.daily_trends}
        title={`Trends for ${categoryData.name}`}
        subtitle="Daily page metric aggregation across all active URLs in this category"
      />

      {/* Top Gainers & Top Decliners Widgets */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Largest Declines */}
        <div className="bg-slate-900/90 rounded-2xl p-5 border border-slate-800">
          <div className="flex items-center space-x-2 text-rose-400 mb-4">
            <TrendingDown className="w-5 h-5" />
            <h2 className="text-sm font-bold text-white tracking-tight">Largest Traffic Declines (28d)</h2>
          </div>
          <div className="space-y-2.5">
            {categoryData.top_declines?.map((p: any) => (
              <div key={p.id} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs">
                <div className="min-w-0 pr-3">
                  <Link to={`/pages/${p.id}`} className="font-semibold text-slate-200 hover:text-indigo-400 truncate block">
                    {p.full_url}
                  </Link>
                  <span className="text-[11px] text-slate-500">
                    Clicks: {p.metrics.current.clicks} (Prev: {p.metrics.previous.clicks})
                  </span>
                </div>
                <div className="text-right shrink-0">
                  <span className="font-bold text-rose-400 block">{p.metrics.click_diff} clicks</span>
                  <span className="text-[11px] font-semibold text-rose-400">{p.metrics.click_pct_change}%</span>
                </div>
              </div>
            ))}
            {(!categoryData.top_declines || categoryData.top_declines.length === 0) && (
              <p className="text-xs text-slate-500 py-3">No pages experiencing traffic loss in this period.</p>
            )}
          </div>
        </div>

        {/* Largest Improvements */}
        <div className="bg-slate-900/90 rounded-2xl p-5 border border-slate-800">
          <div className="flex items-center space-x-2 text-emerald-400 mb-4">
            <TrendingUp className="w-5 h-5" />
            <h2 className="text-sm font-bold text-white tracking-tight">Largest Traffic Improvements (28d)</h2>
          </div>
          <div className="space-y-2.5">
            {categoryData.top_improvements?.map((p: any) => (
              <div key={p.id} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs">
                <div className="min-w-0 pr-3">
                  <Link to={`/pages/${p.id}`} className="font-semibold text-slate-200 hover:text-indigo-400 truncate block">
                    {p.full_url}
                  </Link>
                  <span className="text-[11px] text-slate-500">
                    Clicks: {p.metrics.current.clicks} (Prev: {p.metrics.previous.clicks})
                  </span>
                </div>
                <div className="text-right shrink-0">
                  <span className="font-bold text-emerald-400 block">+{p.metrics.click_diff} clicks</span>
                  <span className="text-[11px] font-semibold text-emerald-400">+{p.metrics.click_pct_change}%</span>
                </div>
              </div>
            ))}
            {(!categoryData.top_improvements || categoryData.top_improvements.length === 0) && (
              <p className="text-xs text-slate-500 py-3">No page gains recorded in this period.</p>
            )}
          </div>
        </div>
      </div>

      {/* Page-Level Comparison Table */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-xl shadow-black/20">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">Mapped Landing Pages</h2>
            <p className="text-xs text-slate-400">Individual URL performance comparing 28 days vs previous 28 days</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3 px-6">Page URL</th>
                <th className="py-3 px-4">Clicks (28d)</th>
                <th className="py-3 px-4">Click Diff / %</th>
                <th className="py-3 px-4">Impressions</th>
                <th className="py-3 px-4">CTR</th>
                <th className="py-3 px-4">Avg Position</th>
                <th className="py-3 px-4">Active Alerts</th>
                {canManage && <th className="py-3 px-4 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {categoryData.pages?.map((p: any) => (
                <tr key={p.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3.5 px-6 font-medium text-white max-w-sm">
                    <Link
                      to={`/pages/${p.id}`}
                      className="hover:text-indigo-400 font-semibold truncate block"
                      title={p.full_url}
                    >
                      {p.full_url}
                    </Link>
                  </td>
                  <td className="py-3.5 px-4 font-bold text-white">
                    {p.metrics.current.clicks.toLocaleString()}
                  </td>
                  <td className="py-3.5 px-4">
                    <span
                      className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded font-bold text-[11px] ${
                        p.metrics.click_pct_change >= 0
                          ? 'bg-emerald-500/15 text-emerald-400'
                          : 'bg-rose-500/15 text-rose-400'
                      }`}
                    >
                      <span>{p.metrics.click_diff > 0 ? '+' : ''}{p.metrics.click_diff}</span>
                      <span>({p.metrics.click_pct_change}%)</span>
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-300">
                    {p.metrics.current.impressions.toLocaleString()}
                  </td>
                  <td className="py-3.5 px-4 text-slate-300 font-medium">
                    {p.metrics.current.ctr}%
                  </td>
                  <td className="py-3.5 px-4 font-semibold">
                    <span
                      className={
                        p.metrics.position_status === 'IMPROVED'
                          ? 'text-emerald-400'
                          : p.metrics.position_status === 'DECLINED'
                          ? 'text-rose-400'
                          : 'text-slate-300'
                      }
                    >
                      {p.metrics.current.position}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    {p.active_alerts > 0 ? (
                      <span className="px-2 py-0.5 rounded-full font-bold text-[11px] bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center space-x-1 w-max">
                        <AlertTriangle className="w-3 h-3" />
                        <span>{p.active_alerts} alert(s)</span>
                      </span>
                    ) : (
                      <span className="text-slate-500 text-[11px]">Normal</span>
                    )}
                  </td>
                  {canManage && (
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleRemovePage(p.id, p.full_url)}
                        className="p-1 rounded text-slate-500 hover:text-rose-400 transition-colors"
                        title="Remove page from category"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Category Active Alerts Section */}
      {categoryData.alerts && categoryData.alerts.length > 0 && (
        <div className="bg-slate-900/90 rounded-2xl p-5 border border-slate-800">
          <h2 className="text-base font-bold text-white tracking-tight mb-4 flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-amber-400" />
            <span>Category Alerts History</span>
          </h2>
          <div className="space-y-2">
            {categoryData.alerts.map((a: any) => (
              <div
                key={a.id}
                className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs"
              >
                <div className="flex items-center space-x-3">
                  <StatusBadge status={a.severity} type="severity" />
                  <div>
                    <p className="font-semibold text-slate-200">{a.page_url}</p>
                    <p className="text-[11px] text-slate-400">
                      Type: <span className="font-medium text-slate-300">{a.alert_type}</span> • Detected on{' '}
                      {a.detection_date} • Change: {a.pct_change}%
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <StatusBadge status={a.status} type="review" />
                  {a.status === 'PENDING' && canManage && (
                    <button
                      onClick={() => handleReviewAlert(a.id)}
                      className="px-2.5 py-1 rounded-lg bg-indigo-600/80 hover:bg-indigo-600 text-white text-[11px] font-semibold"
                    >
                      Mark Reviewed
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ADD PAGE MODAL WITH DUAL-MODE (BULK MULTIPLE URLS & SINGLE URL) */}
      {isAddPageOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 rounded-2xl max-w-xl w-full p-6 border border-slate-800 shadow-2xl my-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                <Layers className="w-5 h-5 text-indigo-400" />
                <span>Map Landing Page URLs</span>
              </h2>

              {/* Mode Switcher */}
              <div className="flex items-center p-1 bg-slate-950 rounded-xl border border-slate-800 text-xs self-start">
                <button
                  type="button"
                  onClick={() => setAddMode('bulk')}
                  className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                    addMode === 'bulk'
                      ? 'bg-indigo-600 text-white shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Bulk Multiple URLs
                </button>
                <button
                  type="button"
                  onClick={() => setAddMode('single')}
                  className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                    addMode === 'single'
                      ? 'bg-indigo-600 text-white shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Single URL
                </button>
              </div>
            </div>

            <p className="text-xs text-slate-400 mb-4">
              Map landing pages to <span className="text-white font-semibold">{categoryData.name}</span>. UTM tracking parameters (utm_*, gclid) and trailing slashes are cleaned automatically.
            </p>

            {addError && (
              <div className="mb-4 p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{addError}</span>
              </div>
            )}

            <form onSubmit={handleAddPageSubmit} className="space-y-4">
              {addMode === 'bulk' ? (
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-xs font-semibold text-slate-300">
                      Paste Landing Page URLs (One per line or comma-separated) *
                    </label>
                    <span className="text-[11px] font-semibold text-indigo-400">
                      {parseBulkUrls(bulkUrlsText).length} URL(s) detected
                    </span>
                  </div>

                  <textarea
                    rows={6}
                    required
                    value={bulkUrlsText}
                    onChange={(e) => handleBulkTextChange(e.target.value)}
                    placeholder={"https://craftyartapp.com/templates/wedding-invitations\nhttps://craftyartapp.com/templates/birthday-invitations\nhttps://craftyartapp.com/templates/baby-shower-invitations"}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs font-mono focus:outline-none focus:border-indigo-500 leading-relaxed"
                  />

                  {validatingBulk && (
                    <p className="text-[11px] text-slate-400 animate-pulse mt-1">Validating URLs & checking for duplicates...</p>
                  )}

                  {bulkCheckResult && (
                    <div className="mt-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                      {/* Summary badges */}
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        <span className="px-2.5 py-1 rounded-lg bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-semibold flex items-center space-x-1">
                          <CheckCircle className="w-3.5 h-3.5" />
                          <span>{bulkCheckResult.total_valid} Ready to Add</span>
                        </span>

                        {bulkCheckResult.total_warnings > 0 && (
                          <span className="px-2.5 py-1 rounded-lg bg-amber-500/15 text-amber-400 border border-amber-500/30 font-semibold flex items-center space-x-1" title="Already mapped in other categories (potential double counting in category totals)">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            <span>{bulkCheckResult.total_warnings} Cross-Category Warning(s)</span>
                          </span>
                        )}

                        {bulkCheckResult.total_duplicates > 0 && (
                          <span className="px-2.5 py-1 rounded-lg bg-rose-500/15 text-rose-400 border border-rose-500/30 font-semibold flex items-center space-x-1">
                            <XCircle className="w-3.5 h-3.5" />
                            <span>{bulkCheckResult.total_duplicates} Duplicate(s) (Will Skip)</span>
                          </span>
                        )}
                      </div>

                      {/* URL Preview List */}
                      <div className="max-h-36 overflow-y-auto divide-y divide-slate-800/80 pr-1">
                        {bulkCheckResult.items.map((item: any, idx: number) => (
                          <div key={idx} className="py-1.5 flex items-start justify-between text-[11px] gap-2">
                            <span className="text-slate-300 font-mono truncate max-w-xs">{item.url}</span>
                            <div className="shrink-0 text-right">
                              {item.is_duplicate_in_category ? (
                                <span className="text-rose-400 font-medium">Duplicate (Skip)</span>
                              ) : item.is_mapped_to_other_categories ? (
                                <span className="text-amber-400 font-medium" title={item.warning}>
                                  Mapped in {item.other_category_names.join(', ')}
                                </span>
                              ) : (
                                <span className="text-emerald-400 font-medium">✓ New Page</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Page Full URL *</label>
                  <input
                    type="url"
                    required
                    value={newUrl}
                    onChange={(e) => handleUrlChange(e.target.value)}
                    placeholder="https://craftyartapp.com/templates/wedding-invitations"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                  />

                  {urlWarning && (
                    <div className="mt-3 p-3 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs flex items-start space-x-2">
                      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>{urlWarning}</span>
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsAddPageOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingLoading}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50 shadow-lg shadow-indigo-600/30"
                >
                  {addingLoading
                    ? 'Saving...'
                    : addMode === 'bulk'
                    ? `Add ${bulkCheckResult?.total_valid ?? parseBulkUrls(bulkUrlsText).length} Page(s)`
                    : 'Add Single Page'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
