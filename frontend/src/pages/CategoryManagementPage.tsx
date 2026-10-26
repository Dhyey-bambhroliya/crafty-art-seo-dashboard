import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  FolderTree, Plus, Search, Edit2, Trash2, ChevronRight, User,
  FileText, AlertCircle, CheckCircle, Shield
} from 'lucide-react';
import { api } from '../services/api';
import { Category, User as UserType } from '../types';
import { useAuth } from '../context/AuthContext';

export const CategoryManagementPage: React.FC = () => {
  const { user, role } = useAuth();
  const isManager = role === 'MANAGER';

  const [categories, setCategories] = useState<Category[]>([]);
  const [leaders, setLeaders] = useState<UserType[]>([]);
  const [search, setSearch] = useState('');
  const [leaderFilter, setLeaderFilter] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);

  // Form states
  const [catName, setCatName] = useState('');
  const [catDesc, setCatDesc] = useState('');
  const [catLeaderId, setCatLeaderId] = useState<number>(user?.id || 1);
  const [formError, setFormError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [catsRes, leadersRes] = await Promise.all([
        api.getCategories({ search: search || undefined, leader_id: leaderFilter }),
        api.getLeaders(),
      ]);
      setCategories(catsRes);
      setLeaders(leadersRes);
      if (leadersRes.length > 0 && isManager && !catLeaderId) {
        setCatLeaderId(leadersRes[0].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [search, leaderFilter]);

  const handleOpenCreate = () => {
    setCatName('');
    setCatDesc('');
    setCatLeaderId(isManager ? (leaders[0]?.id || user?.id || 1) : (user?.id || 1));
    setFormError(null);
    setIsCreateOpen(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setActionLoading(true);

    try {
      await api.createCategory({
        name: catName,
        description: catDesc || undefined,
        assigned_leader_id: isManager ? catLeaderId : (user?.id || 1),
      });
      setIsCreateOpen(false);
      loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create category.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenEdit = (category: Category) => {
    setEditingCategory(category);
    setCatName(category.name);
    setCatDesc(category.description || '');
    setCatLeaderId(category.assigned_leader_id);
    setFormError(null);
    setIsEditOpen(true);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCategory) return;
    setFormError(null);
    setActionLoading(true);

    try {
      await api.updateCategory(editingCategory.id, {
        name: catName,
        description: catDesc,
        assigned_leader_id: isManager ? catLeaderId : undefined,
      });
      setIsEditOpen(false);
      loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to update category.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async (category: Category) => {
    if (!window.confirm(`Are you sure you want to delete category '${category.name}'? All mapped page associations will be removed.`)) {
      return;
    }
    try {
      await api.deleteCategory(category.id);
      loadData();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
            <FolderTree className="w-6 h-6 text-indigo-400" />
            <span>Category Management</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Organize Crafty Art templates into categories, assign leadership, and track mapped SEO page URLs.
          </p>
        </div>

        <button
          onClick={handleOpenCreate}
          className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-all self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>New Category</span>
        </button>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/90 p-3 rounded-2xl border border-slate-800">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search category name..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-950 text-slate-200 text-xs border border-slate-800 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {isManager && (
          <select
            value={leaderFilter || ''}
            onChange={(e) => setLeaderFilter(e.target.value ? Number(e.target.value) : undefined)}
            className="bg-slate-950 text-slate-200 text-xs px-3 py-2 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Assigned Leaders</option>
            {leaders.map((l) => (
              <option key={l.id} value={l.id}>
                {l.full_name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Categories Table */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-xl shadow-black/20">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-6">Category Name</th>
                <th className="py-3.5 px-6">Assigned Team Leader</th>
                <th className="py-3.5 px-6">Mapped Pages</th>
                <th className="py-3.5 px-6">Status</th>
                <th className="py-3.5 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {loading && categories.length === 0 ? (
                <>
                  {[1, 2, 3, 4, 5].map((i) => (
                    <tr key={`skel-${i}`} className="animate-pulse">
                      <td className="py-4 px-6">
                        <div className="h-4 bg-slate-800 rounded w-48 mb-2"></div>
                        <div className="h-3 bg-slate-800/60 rounded w-32"></div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center space-x-2">
                          <div className="w-6 h-6 rounded-full bg-slate-800"></div>
                          <div className="h-4 bg-slate-800 rounded w-24"></div>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="h-6 bg-slate-800 rounded w-20"></div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="h-5 bg-slate-800 rounded-full w-16"></div>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <div className="h-6 bg-slate-800 rounded w-16 ml-auto"></div>
                      </td>
                    </tr>
                  ))}
                </>
              ) : (
                categories.map((cat) => {
                  const canEdit = isManager || Number(cat.assigned_leader_id) === Number(user?.id);

                  return (
                    <tr key={cat.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-4 px-6 font-medium text-white">
                        <Link
                          to={`/categories/${cat.id}`}
                          className="hover:text-indigo-400 font-semibold text-sm transition-colors block"
                        >
                          {cat.name}
                        </Link>
                        {cat.description && (
                          <p className="text-slate-400 text-xs mt-0.5 max-w-md truncate">{cat.description}</p>
                        )}
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center space-x-2">
                          <div className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-300 uppercase">
                            {cat.leader_name?.charAt(0) || 'L'}
                          </div>
                          <span className="font-medium text-slate-200">{cat.leader_name}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 font-semibold text-slate-200">
                        <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-800/80 border border-slate-700/60">
                          <FileText className="w-3.5 h-3.5 text-indigo-400" />
                          <span>{cat.page_count} pages</span>
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          {cat.status}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <Link
                            to={`/categories/${cat.id}`}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                            title="Open details"
                          >
                            <ChevronRight className="w-4 h-4" />
                          </Link>
                          {canEdit && (
                            <button
                              onClick={() => handleOpenEdit(cat)}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 transition-colors"
                              title="Edit Category"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                          )}
                          {canEdit && (
                            <button
                              onClick={() => handleDelete(cat)}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                              title="Delete Category"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
              {categories.length === 0 && !loading && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    No categories found matching your query.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* CREATE MODAL */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 rounded-2xl max-w-md w-full p-6 border border-slate-800 shadow-2xl">
            <h2 className="text-lg font-bold text-white mb-4">Create New SEO Category</h2>

            {formError && (
              <div className="mb-4 p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Category Name *</label>
                <input
                  type="text"
                  required
                  value={catName}
                  onChange={(e) => setCatName(e.target.value)}
                  placeholder="e.g. Wedding Invitation Templates"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Description (Optional)</label>
                <textarea
                  rows={3}
                  value={catDesc}
                  onChange={(e) => setCatDesc(e.target.value)}
                  placeholder="Category scope and purpose..."
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Assigned Team Leader *</label>
                {isManager ? (
                  <select
                    value={catLeaderId}
                    onChange={(e) => setCatLeaderId(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500 font-medium"
                  >
                    {leaders.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.full_name} ({l.email})
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    disabled
                    value={`${user?.full_name} (Self - Team Leader)`}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/50 border border-slate-800 text-slate-400 text-xs cursor-not-allowed"
                  />
                )}
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {actionLoading ? 'Creating...' : 'Create Category'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT MODAL */}
      {isEditOpen && editingCategory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 rounded-2xl max-w-md w-full p-6 border border-slate-800 shadow-2xl">
            <h2 className="text-lg font-bold text-white mb-4">Edit Category: {editingCategory.name}</h2>

            {formError && (
              <div className="mb-4 p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleEditSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Category Name *</label>
                <input
                  type="text"
                  required
                  value={catName}
                  onChange={(e) => setCatName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Description</label>
                <textarea
                  rows={3}
                  value={catDesc}
                  onChange={(e) => setCatDesc(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              {isManager && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Reassign Team Leader</label>
                  <select
                    value={catLeaderId}
                    onChange={(e) => setCatLeaderId(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500 font-medium"
                  >
                    {leaders.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.full_name} ({l.email})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsEditOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {actionLoading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
