import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, ExternalLink, MousePointer, Eye, Percent, Target,
  AlertTriangle, CheckCircle, Calendar, FolderTree, User
} from 'lucide-react';
import { StatCard } from '../components/common/StatCard';
import { TrendChart } from '../components/common/TrendChart';
import { StatusBadge } from '../components/common/StatusBadge';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export const PageDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const pageId = Number(id);
  const { role, user } = useAuth();
  const isManager = role === 'MANAGER';

  const [pageData, setPageData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await api.getPageDetail(pageId);
      setPageData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (pageId) loadData();
  }, [pageId]);

  const handleReviewAlert = async (alertId: number) => {
    try {
      await api.updateAlertStatus(alertId, 'REVIEWED');
      loadData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  if (loading || !pageData) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-48 bg-slate-900 rounded" />
        <div className="h-32 bg-slate-900 rounded-2xl" />
        <div className="h-64 bg-slate-900 rounded-2xl" />
      </div>
    );
  }

  const comp = pageData.comparison;
  const canManage = isManager || pageData.assigned_leader_id === user?.id;

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation */}
      <div>
        <Link
          to={`/categories/${pageData.category_id}`}
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-400 hover:text-white transition-colors mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Category: {pageData.category_name}</span>
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-white tracking-tight truncate flex items-center space-x-2">
              <span className="truncate">{pageData.full_url}</span>
              <a
                href={pageData.full_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-400 hover:text-indigo-400 transition-colors"
                title="Visit live page in new tab"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            </h1>
            <p className="text-xs text-slate-400 mt-1 flex items-center space-x-3">
              <span className="flex items-center space-x-1">
                <FolderTree className="w-3.5 h-3.5 text-indigo-400" />
                <span className="text-slate-300 font-medium">{pageData.category_name}</span>
              </span>
              <span>•</span>
              <span className="flex items-center space-x-1">
                <User className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-slate-300 font-medium">{pageData.leader_name}</span>
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="28-Day Clicks"
          currentValue={comp.current.clicks}
          previousValue={comp.previous.clicks}
          diff={comp.click_diff}
          pctChange={comp.click_pct_change}
          icon={<MousePointer className="w-4 h-4 text-indigo-400" />}
        />
        <StatCard
          title="28-Day Impressions"
          currentValue={comp.current.impressions}
          previousValue={comp.previous.impressions}
          diff={comp.impression_diff}
          pctChange={comp.impression_pct_change}
          icon={<Eye className="w-4 h-4 text-violet-400" />}
        />
        <StatCard
          title="Click-Through Rate"
          currentValue={comp.current.ctr}
          previousValue={comp.previous.ctr}
          diff={comp.ctr_diff}
          suffix="%"
          icon={<Percent className="w-4 h-4 text-emerald-400" />}
        />
        <StatCard
          title="Average Search Rank"
          currentValue={comp.current.position}
          previousValue={comp.previous.position}
          diff={comp.position_diff}
          isPosition={true}
          icon={<Target className="w-4 h-4 text-amber-400" />}
        />
      </div>

      {/* Daily Performance Trend Chart */}
      <TrendChart
        data={pageData.daily_trends}
        title="Page Traffic Performance"
        subtitle="Daily comparison for this URL over the 28-day window vs preceding 28 days"
      />

      {/* Alert History Section */}
      <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 shadow-xl shadow-black/20">
        <h2 className="text-base font-bold text-white tracking-tight mb-4 flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <span>Page Alert History</span>
        </h2>

        {pageData.alerts && pageData.alerts.length > 0 ? (
          <div className="space-y-3">
            {pageData.alerts.map((alert: any) => (
              <div
                key={alert.id}
                className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
              >
                <div className="flex items-start space-x-3">
                  <StatusBadge status={alert.severity} type="severity" />
                  <div>
                    <p className="font-semibold text-slate-200 text-sm">{alert.alert_type}</p>
                    <p className="text-slate-400 mt-0.5">
                      Change: <span className="text-rose-400 font-semibold">{alert.pct_change}%</span> • Detected:{' '}
                      <span className="text-slate-300 font-medium">{alert.detection_date}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <StatusBadge status={alert.status} type="review" />
                  {alert.status === 'PENDING' && canManage && (
                    <button
                      onClick={() => handleReviewAlert(alert.id)}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-colors"
                    >
                      Acknowledge Review
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500 text-xs">
            No active or past alerts recorded for this URL.
          </div>
        )}
      </div>
    </div>
  );
};
