import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText, Search, ArrowUpDown, ExternalLink, ChevronRight,
  TrendingDown, AlertTriangle, Filter, FolderTree, User
} from 'lucide-react';
import { api } from '../services/api';
import { Category, User as UserType } from '../types';
import { useAuth } from '../context/AuthContext';

export const PagesMonitoringPage: React.FC = () => {
  const { user, role } = useAuth();
  const isManager = role === 'MANAGER';

  const [pages, setPages] = useState<any[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [leaders, setLeaders] = useState<UserType[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters & Sorting
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<number | undefined>(undefined);
  const [leaderFilter, setLeaderFilter] = useState<number | undefined>(
    !isManager && user ? user.id : undefined
  );
  const [sortBy, setSortBy] = useState<string>('traffic_loss');

  const loadPages = async () => {
    setLoading(true);
    try {
      const [pagesRes, catsRes, leadersRes] = await Promise.all([
        api.getPagesMonitoring({
          category_id: categoryFilter,
          leader_id: leaderFilter,
          sort_by: sortBy,
          search: search || undefined,
        }),
        api.getCategories(),
        api.getLeaders(),
      ]);
      setPages(pagesRes);
      setCategories(catsRes);
      setLeaders(leadersRes);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPages();
  }, [categoryFilter, leaderFilter, sortBy, search]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
          <FileText className="w-6 h-6 text-indigo-400" />
          <span>Page-Level SEO Monitoring</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Detailed metrics comparison comparing the latest 28 complete days vs the preceding 28 complete days across Crafty Art landing pages.
        </p>
      </div>

      {/* Filter and Sort Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/90 p-3 rounded-2xl border border-slate-800">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search landing page URL..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-950 text-slate-200 text-xs border border-slate-800 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Sort By Dropdown */}
          <div className="flex items-center space-x-1.5 bg-slate-950 px-3 py-2 rounded-xl border border-slate-800">
            <ArrowUpDown className="w-3.5 h-3.5 text-indigo-400" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-transparent text-slate-200 text-xs focus:outline-none font-medium"
            >
              <option value="traffic_loss">Largest Traffic Loss (Clicks)</option>
              <option value="pct_loss">Largest % Decline</option>
              <option value="impressions_loss">Largest Impression Loss</option>
              <option value="clicks">Highest Current Clicks</option>
              <option value="impressions">Highest Impressions</option>
            </select>
          </div>

          {/* Category Filter */}
          <select
            value={categoryFilter || ''}
            onChange={(e) => setCategoryFilter(e.target.value ? Number(e.target.value) : undefined)}
            className="bg-slate-950 text-slate-200 text-xs px-3 py-2 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          {/* Leader Filter */}
          {isManager && (
            <select
              value={leaderFilter || ''}
              onChange={(e) => setLeaderFilter(e.target.value ? Number(e.target.value) : undefined)}
              className="bg-slate-950 text-slate-200 text-xs px-3 py-2 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Leaders</option>
              {leaders.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.full_name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-xl shadow-black/20">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-6">Landing Page URL</th>
                <th className="py-3.5 px-4">Category</th>
                <th className="py-3.5 px-4">Leader</th>
                <th className="py-3.5 px-4">Current Clicks</th>
                <th className="py-3.5 px-4">Click Change</th>
                <th className="py-3.5 px-4">Impressions</th>
                <th className="py-3.5 px-4">CTR</th>
                <th className="py-3.5 px-4">Avg Position</th>
                <th className="py-3.5 px-4">Alerts</th>
                <th className="py-3.5 px-6 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {pages.map((p) => {
                const isDecline = p.metrics.click_pct_change < 0;

                return (
                  <tr key={p.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-4 px-6 max-w-sm">
                      <Link
                        to={`/pages/${p.id}`}
                        className="font-semibold text-white hover:text-indigo-400 block truncate transition-colors"
                        title={p.full_url}
                      >
                        {p.full_url}
                      </Link>
                    </td>

                    <td className="py-4 px-4 font-medium text-slate-300 truncate max-w-[150px]">
                      {p.category_name}
                    </td>

                    <td className="py-4 px-4 text-slate-400 text-[11px] truncate">
                      {p.leader_name}
                    </td>

                    <td className="py-4 px-4 font-bold text-white text-sm">
                      {p.metrics.current.clicks.toLocaleString()}
                    </td>

                    <td className="py-4 px-4">
                      <span
                        className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded font-bold text-[11px] ${
                          isDecline
                            ? 'bg-rose-500/15 text-rose-400 border border-rose-500/25'
                            : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25'
                        }`}
                      >
                        <span>{p.metrics.click_diff > 0 ? '+' : ''}{p.metrics.click_diff}</span>
                        <span>({p.metrics.click_pct_change}%)</span>
                      </span>
                    </td>

                    <td className="py-4 px-4 text-slate-300">
                      {p.metrics.current.impressions.toLocaleString()}
                    </td>

                    <td className="py-4 px-4 font-medium text-slate-300">
                      {p.metrics.current.ctr}%
                    </td>

                    <td className="py-4 px-4 font-semibold">
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

                    <td className="py-4 px-4">
                      {p.active_alerts > 0 ? (
                        <span className="px-2 py-0.5 rounded-full font-bold text-[11px] bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center space-x-1 w-max">
                          <AlertTriangle className="w-3 h-3" />
                          <span>{p.active_alerts}</span>
                        </span>
                      ) : (
                        <span className="text-slate-500 text-[11px]">0</span>
                      )}
                    </td>

                    <td className="py-4 px-6 text-right">
                      <Link
                        to={`/pages/${p.id}`}
                        className="inline-flex items-center space-x-1 text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                      >
                        <span>Report</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                );
              })}

              {pages.length === 0 && !loading && (
                <tr>
                  <td colSpan={10} className="py-10 text-center text-slate-500">
                    No mapped pages found matching filter criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
