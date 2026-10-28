import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  CheckSquare, ArrowLeft, Filter, Search, Calendar, User, Clock,
  AlertTriangle, CheckCircle, Trash2, Edit2, AlertCircle, Sparkles,
  ExternalLink, ChevronRight
} from 'lucide-react';
import { festivalApi } from '../services/festivalApi';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Festival, FestivalTask } from '../types/festival';
import { User as UserType } from '../types';

export const FestivalTasksPage: React.FC = () => {
  const { user, role } = useAuth();
  const isManager = role === 'MANAGER';

  const [tasks, setTasks] = useState<FestivalTask[]>([]);
  const [festivals, setFestivals] = useState<Festival[]>([]);
  const [leaders, setLeaders] = useState<UserType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedFestivalId, setSelectedFestivalId] = useState<number | undefined>(undefined);
  const [selectedMilestone, setSelectedMilestone] = useState<string>('ALL');
  const [selectedLeaderId, setSelectedLeaderId] = useState<number | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');
  const [showOverdueOnly, setShowOverdueOnly] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [allTasks, allFests, leadersRes] = await Promise.all([
        festivalApi.getAllTasks({
          festival_id: selectedFestivalId,
          milestone_stage: selectedMilestone !== 'ALL' ? selectedMilestone : undefined,
        }),
        festivalApi.getFestivals(),
        isManager ? api.getLeaders() : Promise.resolve([]),
      ]);

      setTasks(allTasks);
      setFestivals(allFests);
      if (isManager) setLeaders(leadersRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load task board.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedFestivalId, selectedMilestone]);

  const handleUpdateStatus = async (festivalId: number, taskId: number, newStatus: string) => {
    try {
      await festivalApi.updateFestivalTaskStatus(festivalId, taskId, newStatus);
      // Optimistic update in UI
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: newStatus as any } : t))
      );
    } catch (err: any) {
      alert(err.message || 'Failed to update task status.');
      loadData();
    }
  };

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const filteredTasks = tasks.filter((t) => {
    if (selectedLeaderId && t.assigned_user_id !== selectedLeaderId) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchTitle = t.title.toLowerCase().includes(q);
      const matchDesc = t.description?.toLowerCase().includes(q);
      if (!matchTitle && !matchDesc) return false;
    }
    if (showOverdueOnly) {
      if (!t.due_date || t.status === 'COMPLETED') return false;
      const d = new Date(t.due_date);
      return d < today;
    }
    return true;
  });

  const columns = [
    {
      status: 'NOT_STARTED',
      title: 'Not Started',
      badgeClass: 'bg-slate-800 text-slate-400 border-slate-700',
    },
    {
      status: 'IN_PROGRESS',
      title: 'In Progress',
      badgeClass: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30',
    },
    {
      status: 'READY_FOR_REVIEW',
      title: 'Ready for Review',
      badgeClass: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    },
    {
      status: 'COMPLETED',
      title: 'Completed',
      badgeClass: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          to="/festivals"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-400 hover:text-white transition-colors mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Festival Dashboard</span>
        </Link>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="p-2 rounded-xl bg-emerald-500/20 text-emerald-400">
                <CheckSquare className="w-5 h-5" />
              </span>
              <h1 className="text-2xl font-bold text-white tracking-tight">Preparation Task Board</h1>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Kanban task workflow across all scheduled festivals, content preparations, and technical optimizations.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowOverdueOnly(!showOverdueOnly)}
              className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all flex items-center space-x-1.5 ${
                showOverdueOnly
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/50 shadow-md shadow-rose-500/10'
                  : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
              <span>Show Overdue Only</span>
            </button>
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search task title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Festival Filter */}
        <div className="flex items-center space-x-2">
          <span className="text-xs text-slate-400 font-medium shrink-0">Festival:</span>
          <select
            value={selectedFestivalId || ''}
            onChange={(e) => setSelectedFestivalId(e.target.value ? Number(e.target.value) : undefined)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Festivals</option>
            {festivals.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name} ({f.country_code})
              </option>
            ))}
          </select>
        </div>

        {/* Milestone Stage */}
        <div className="flex items-center space-x-2">
          <span className="text-xs text-slate-400 font-medium shrink-0">Milestone:</span>
          <select
            value={selectedMilestone}
            onChange={(e) => setSelectedMilestone(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Milestones</option>
            <option value="T_MINUS_60">T-60 Days</option>
            <option value="T_MINUS_30">T-30 Days</option>
            <option value="T_MINUS_15">T-15 Days</option>
            <option value="T_MINUS_7">T-7 Days</option>
            <option value="FESTIVAL_WEEK">Festival Week</option>
            <option value="POST_FESTIVAL">Post Festival</option>
          </select>
        </div>

        {/* Team Leader Filter (Manager Only) */}
        {isManager ? (
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400 font-medium shrink-0">Assignee:</span>
            <select
              value={selectedLeaderId || ''}
              onChange={(e) => setSelectedLeaderId(e.target.value ? Number(e.target.value) : undefined)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Assignees</option>
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
            <span>Scope: {user?.full_name}</span>
          </div>
        )}
      </div>

      {/* Kanban Board */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-80 bg-slate-900/60 rounded-2xl animate-pulse border border-slate-800" />
          ))}
        </div>
      ) : error ? (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-6 text-center text-xs text-rose-300">
          <AlertCircle className="w-6 h-6 text-rose-400 mx-auto mb-2" />
          <span>{error}</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-start">
          {columns.map((col) => {
            const colTasks = filteredTasks.filter((t) => t.status === col.status);

            return (
              <div
                key={col.status}
                className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800 shadow-xl shadow-black/20 flex flex-col justify-between min-h-[500px]"
              >
                <div>
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <span className="font-bold text-xs text-white uppercase tracking-wider">{col.title}</span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${col.badgeClass}`}>
                      {colTasks.length}
                    </span>
                  </div>

                  <div className="mt-3 space-y-3">
                    {colTasks.length === 0 ? (
                      <div className="py-12 text-center text-slate-600 text-xs">No tasks in this stage</div>
                    ) : (
                      colTasks.map((t) => {
                        const isOverdue =
                          t.due_date &&
                          t.status !== 'COMPLETED' &&
                          new Date(t.due_date) < today;

                        // Find festival name
                        const fest = festivals.find((f) => f.id === t.festival_id);

                        return (
                          <div
                            key={t.id}
                            className={`bg-slate-950 p-4 rounded-xl border transition-all ${
                              isOverdue
                                ? 'border-rose-500/50 shadow-md shadow-rose-500/10'
                                : 'border-slate-800/90 hover:border-slate-700'
                            }`}
                          >
                            {/* Festival Name Header */}
                            {fest && (
                              <Link
                                to={`/festivals/${fest.id}`}
                                className="text-[10px] font-bold text-indigo-400 hover:underline inline-flex items-center space-x-1 mb-1 block"
                              >
                                <Sparkles className="w-3 h-3" />
                                <span>{fest.name}</span>
                              </Link>
                            )}

                            <h4 className="font-bold text-xs text-white leading-snug">{t.title}</h4>

                            {t.description && (
                              <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{t.description}</p>
                            )}

                            <div className="mt-3 pt-2.5 border-t border-slate-800/80 space-y-1.5 text-[11px]">
                              <div className="flex items-center justify-between text-slate-400">
                                <span>Stage:</span>
                                <span className="text-slate-300 font-mono text-[10px] bg-slate-900 px-1.5 py-0.2 rounded border border-slate-800">
                                  {t.milestone_stage}
                                </span>
                              </div>

                              <div className="flex items-center justify-between text-slate-400">
                                <span>Assignee:</span>
                                <span className="text-slate-300 font-medium">
                                  {t.assigned_user_name || 'Unassigned'}
                                </span>
                              </div>

                              {t.due_date && (
                                <div className="flex items-center justify-between">
                                  <span className="text-slate-400">Due Date:</span>
                                  <span
                                    className={`font-semibold ${
                                      isOverdue ? 'text-rose-400 flex items-center space-x-1' : 'text-slate-300'
                                    }`}
                                  >
                                    {isOverdue && <AlertTriangle className="w-3 h-3 text-rose-400" />}
                                    <span>{t.due_date}</span>
                                  </span>
                                </div>
                              )}
                            </div>

                            {/* Status Change Selector */}
                            <div className="mt-3">
                              <select
                                value={t.status}
                                onChange={(e) => handleUpdateStatus(t.festival_id, t.id, e.target.value)}
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
      )}
    </div>
  );
};
export default FestivalTasksPage;
