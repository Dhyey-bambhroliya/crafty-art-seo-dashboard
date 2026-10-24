import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Users, FolderTree, FileText, MousePointer, Eye, Percent,
  Target, AlertTriangle, ArrowUpRight, Filter, ChevronRight, Sparkles
} from 'lucide-react';
import { StatCard } from '../components/common/StatCard';
import { TrendChart } from '../components/common/TrendChart';
import { api } from '../services/api';
import { DashboardKPIs, DailyTrendPoint, Category, User } from '../types';
import { useAuth } from '../context/AuthContext';

export const DashboardPage: React.FC = () => {
  const { user, role } = useAuth();
  const isManager = role === 'MANAGER';

  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [trends, setTrends] = useState<DailyTrendPoint[]>([]);
  const [categoriesSummary, setCategoriesSummary] = useState<any[]>([]);
  const [leaders, setLeaders] = useState<User[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);

  // Filter states
  const [selectedLeaderId, setSelectedLeaderId] = useState<number | undefined>(
    !isManager && user ? user.id : undefined
  );
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [kpisRes, trendsRes, catsSummaryRes, leadersRes, allCatsRes] = await Promise.all([
        api.getDashboardKPIs({ leader_id: selectedLeaderId, category_id: selectedCategoryId }),
        api.getDashboardTrends({ leader_id: selectedLeaderId, category_id: selectedCategoryId }),
        api.getCategoriesSummary(selectedLeaderId),
        api.getLeaders(),
        api.getCategories({ leader_id: selectedLeaderId }),
      ]);

      setKpis(kpisRes);
      setTrends(trendsRes);
      setCategoriesSummary(catsSummaryRes);
      setLeaders(leadersRes);
      setCategories(allCatsRes);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [selectedLeaderId, selectedCategoryId]);

  return (
    <div className="space-y-6">
      {/* Page Title & Filter Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
            <span>{isManager ? 'SEO Performance Overview' : 'My SEO Workspace'}</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 font-semibold">
              28d vs Previous 28d
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Aggregated page metrics with impression-weighted rankings across Crafty Art categories.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 bg-slate-900/90 p-2 rounded-xl border border-slate-800">
          <div className="flex items-center space-x-1.5 text-xs text-slate-400 px-2 font-medium">
            <Filter className="w-3.5 h-3.5 text-indigo-400" />
            <span>Filters:</span>
          </div>

          {isManager && (
            <select
              value={selectedLeaderId || ''}
              onChange={(e) => {
                setSelectedLeaderId(e.target.value ? Number(e.target.value) : undefined);
                setSelectedCategoryId(undefined);
              }}
              className="bg-slate-950 text-slate-200 text-xs px-3 py-1.5 rounded-lg border border-slate-700/80 focus:outline-none focus:border-indigo-500 font-medium"
            >
              <option value="">All Team Leaders</option>
              {leaders.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.full_name}
                </option>
              ))}
            </select>
          )}

          <select
            value={selectedCategoryId || ''}
            onChange={(e) => setSelectedCategoryId(e.target.value ? Number(e.target.value) : undefined)}
            className="bg-slate-950 text-slate-200 text-xs px-3 py-1.5 rounded-lg border border-slate-700/80 focus:outline-none focus:border-indigo-500 font-medium"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Top KPI Cards Grid */}
      {kpis ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Clicks (28 Days)"
            currentValue={kpis.current_clicks}
            previousValue={kpis.previous_clicks}
            diff={kpis.click_diff}
            pctChange={kpis.click_pct_change}
            icon={<MousePointer className="w-4 h-4 text-indigo-400" />}
          />
          <StatCard
            title="Total Impressions (28 Days)"
            currentValue={kpis.current_impressions}
            previousValue={kpis.previous_impressions}
            diff={kpis.impression_diff}
            pctChange={kpis.impression_pct_change}
            icon={<Eye className="w-4 h-4 text-violet-400" />}
          />
          <StatCard
            title="Average CTR"
            currentValue={kpis.current_ctr}
            previousValue={kpis.previous_ctr}
            diff={Number((kpis.current_ctr - kpis.previous_ctr).toFixed(2))}
            suffix="%"
            icon={<Percent className="w-4 h-4 text-emerald-400" />}
          />
          <StatCard
            title="Avg Position (Weighted)"
            currentValue={kpis.current_avg_position}
            previousValue={kpis.previous_avg_position}
            diff={Number((kpis.current_avg_position - kpis.previous_avg_position).toFixed(2))}
            isPosition={true}
            icon={<Target className="w-4 h-4 text-amber-400" />}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 animate-pulse">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-slate-900 rounded-2xl border border-slate-800" />
          ))}
        </div>
      )}

      {/* Secondary Quick Metrics Cards */}
      {kpis && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                <FolderTree className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-slate-400 font-medium">Mapped Categories</p>
                <p className="text-xl font-bold text-white">{kpis.total_categories}</p>
              </div>
            </div>
            <Link to="/categories" className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center">
              View <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
            </Link>
          </div>

          <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-slate-400 font-medium">Mapped Landing Pages</p>
                <p className="text-xl font-bold text-white">{kpis.total_mapped_pages}</p>
              </div>
            </div>
            <Link to="/pages" className="text-xs text-emerald-400 hover:text-emerald-300 font-medium flex items-center">
              Monitor <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
            </Link>
          </div>

          <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-lg bg-rose-500/10 text-rose-400">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-slate-400 font-medium">Pages With Traffic Decline</p>
                <p className="text-xl font-bold text-rose-400">{kpis.pages_with_decline}</p>
              </div>
            </div>
            <Link to="/alerts" className="text-xs text-rose-400 hover:text-rose-300 font-medium flex items-center">
              Alerts <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
            </Link>
          </div>
        </div>
      )}

      {/* 28-day Over-Time Trend Chart */}
      <TrendChart data={trends} />

      {/* Category Performance Breakdown Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">Category SEO Breakdown</h2>
            <p className="text-xs text-slate-400">Comparison of latest 28 complete days vs previous 28 complete days</p>
          </div>
          <Link to="/categories" className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center space-x-1">
            <span>Manage All Categories</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {categoriesSummary.map((cat) => (
            <div
              key={cat.id}
              className="bg-slate-900/90 rounded-2xl p-5 border border-slate-800 hover:border-slate-700/80 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div>
                    <Link
                      to={`/categories/${cat.id}`}
                      className="text-base font-bold text-white hover:text-indigo-400 transition-colors flex items-center space-x-1.5"
                    >
                      <span>{cat.name}</span>
                      <ArrowUpRight className="w-4 h-4 text-slate-500" />
                    </Link>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Leader: <span className="text-slate-300 font-medium">{cat.leader_name}</span> • {cat.page_count} pages
                    </p>
                  </div>
                  <span className="text-xs px-2.5 py-1 rounded-full font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                    {cat.status}
                  </span>
                </div>

                {/* Metrics Comparison Grid */}
                <div className="grid grid-cols-4 gap-2 mt-4 pt-4 border-t border-slate-800/80 text-xs">
                  <div>
                    <span className="text-slate-400 block text-[11px]">Clicks</span>
                    <span className="font-bold text-white text-sm">{cat.metrics.current.clicks.toLocaleString()}</span>
                    <span
                      className={`block text-[11px] font-semibold ${
                        cat.metrics.click_pct_change >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {cat.metrics.click_pct_change >= 0 ? '+' : ''}
                      {cat.metrics.click_pct_change}%
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-400 block text-[11px]">Impressions</span>
                    <span className="font-bold text-white text-sm">{cat.metrics.current.impressions.toLocaleString()}</span>
                    <span
                      className={`block text-[11px] font-semibold ${
                        cat.metrics.impression_pct_change >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {cat.metrics.impression_pct_change >= 0 ? '+' : ''}
                      {cat.metrics.impression_pct_change}%
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-400 block text-[11px]">CTR</span>
                    <span className="font-bold text-white text-sm">{cat.metrics.current.ctr}%</span>
                    <span className="text-slate-400 text-[11px] block">
                      Prev: {cat.metrics.previous.ctr}%
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-400 block text-[11px]">Position</span>
                    <span className="font-bold text-white text-sm">{cat.metrics.current.position}</span>
                    <span
                      className={`block text-[11px] font-semibold ${
                        cat.metrics.position_status === 'IMPROVED'
                          ? 'text-emerald-400'
                          : cat.metrics.position_status === 'DECLINED'
                          ? 'text-rose-400'
                          : 'text-slate-400'
                      }`}
                    >
                      {cat.metrics.position_status}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/60 flex justify-end">
                <Link
                  to={`/categories/${cat.id}`}
                  className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center space-x-1"
                >
                  <span>Open Category Details</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
