import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Bell, Filter, AlertTriangle, AlertCircle, CheckCircle, Search,
  ArrowUpRight, Sliders, ExternalLink
} from 'lucide-react';
import { StatusBadge } from '../components/common/StatusBadge';
import { api } from '../services/api';
import { Alert, Category, User } from '../types';
import { useAuth } from '../context/AuthContext';

export const AlertsPage: React.FC = () => {
  const { user, role } = useAuth();
  const isManager = role === 'MANAGER';

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [leaders, setLeaders] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('PENDING'); // Default to pending
  const [categoryFilter, setCategoryFilter] = useState<number | undefined>(undefined);
  const [leaderFilter, setLeaderFilter] = useState<number | undefined>(
    !isManager && user ? user.id : undefined
  );
  const [search, setSearch] = useState('');

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const [alertsRes, catsRes, leadersRes] = await Promise.all([
        api.getAlerts({
          severity: severityFilter || undefined,
          status_filter: statusFilter || undefined,
          category_id: categoryFilter,
          leader_id: leaderFilter,
        }),
        api.getCategories(),
        api.getLeaders(),
      ]);
      setAlerts(alertsRes);
      setCategories(catsRes);
      setLeaders(leadersRes);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, [severityFilter, statusFilter, categoryFilter, leaderFilter]);

  const handleUpdateStatus = async (alertId: number, newStatus: 'REVIEWED' | 'DISMISSED') => {
    try {
      await api.updateAlertStatus(alertId, newStatus);
      loadAlerts();
    } catch (err: any) {
      alert(`Action failed: ${err.message}`);
    }
  };

  const filteredAlerts = alerts.filter(
    (a) => !search || a.page_url.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
            <Bell className="w-6 h-6 text-rose-400" />
            <span>SEO Anomaly & Decline Alerts</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Automated notifications when landing pages suffer traffic loss, impression decline, or rank drops.
          </p>
        </div>

        <Link
          to="/settings"
          className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700/80 transition-all self-start sm:self-auto"
        >
          <Sliders className="w-3.5 h-3.5 text-indigo-400" />
          <span>Configure Thresholds</span>
        </Link>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/90 p-3 rounded-2xl border border-slate-800">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search affected URL..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-950 text-slate-200 text-xs border border-slate-800 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 text-slate-200 text-xs px-3 py-2 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Review Statuses</option>
            <option value="PENDING">Pending Action</option>
            <option value="REVIEWED">Reviewed</option>
            <option value="DISMISSED">Dismissed</option>
          </select>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-950 text-slate-200 text-xs px-3 py-2 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical Severity (≥20% loss)</option>
            <option value="WARNING">Warning (≥10% loss)</option>
          </select>

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

      {/* Alerts Table */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-xl shadow-black/20">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-6">Severity & Alert Type</th>
                <th className="py-3.5 px-6">Affected Page URL</th>
                <th className="py-3.5 px-4">Category & Leader</th>
                <th className="py-3.5 px-4">Decline %</th>
                <th className="py-3.5 px-4">Detection Date</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {filteredAlerts.map((a) => {
                const canReview = isManager || a.assigned_leader_id === user?.id;

                return (
                  <tr key={a.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-4 px-6">
                      <div className="flex flex-col space-y-1">
                        <StatusBadge status={a.severity} type="severity" />
                        <span className="font-semibold text-slate-200 text-[11px]">{a.alert_type}</span>
                      </div>
                    </td>

                    <td className="py-4 px-6 max-w-xs">
                      <span className="font-semibold text-white block truncate" title={a.page_url}>
                        {a.page_url}
                      </span>
                      <span className="text-[11px] text-slate-500">
                        Current: {a.current_value.toLocaleString()} vs Prev: {a.previous_value.toLocaleString()}
                      </span>
                    </td>

                    <td className="py-4 px-4">
                      <span className="font-medium text-slate-200 block truncate">{a.category_name}</span>
                      <span className="text-[11px] text-indigo-400">{a.leader_name}</span>
                    </td>

                    <td className="py-4 px-4">
                      <span className="font-bold text-rose-400 text-sm">
                        {a.pct_change > 0 ? `+${a.pct_change}` : `${a.pct_change}`}%
                      </span>
                    </td>

                    <td className="py-4 px-4 text-slate-400 font-medium">
                      {a.detection_date}
                    </td>

                    <td className="py-4 px-4">
                      <StatusBadge status={a.status} type="review" />
                    </td>

                    <td className="py-4 px-6 text-right">
                      {a.status === 'PENDING' && canReview ? (
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => handleUpdateStatus(a.id, 'REVIEWED')}
                            className="px-2.5 py-1 rounded-lg bg-emerald-600/80 hover:bg-emerald-600 text-white font-semibold transition-colors"
                            title="Acknowledge and mark as reviewed"
                          >
                            Review
                          </button>
                          <button
                            onClick={() => handleUpdateStatus(a.id, 'DISMISSED')}
                            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 font-semibold transition-colors"
                            title="Dismiss alert"
                          >
                            Dismiss
                          </button>
                        </div>
                      ) : (
                        <span className="text-slate-500 text-[11px]">Completed</span>
                      )}
                    </td>
                  </tr>
                );
              })}

              {filteredAlerts.length === 0 && !loading && (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-slate-500">
                    No alerts match the selected criteria. All landing pages operating within normal thresholds!
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
