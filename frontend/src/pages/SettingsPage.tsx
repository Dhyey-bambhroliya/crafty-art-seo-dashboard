import React, { useState, useEffect } from 'react';
import {
  Settings, Sliders, Shield, Bell, CheckCircle2, AlertCircle,
  Clock, Database, UserCheck, Save, Trash2, AlertTriangle, RefreshCw
} from 'lucide-react';
import { api } from '../services/api';
import { AlertSetting } from '../types';
import { useAuth } from '../context/AuthContext';

export const SettingsPage: React.FC = () => {
  const { user, role } = useAuth();
  const isManager = role === 'MANAGER';

  const [settings, setSettings] = useState<AlertSetting | null>(null);
  const [clickWarn, setClickWarn] = useState<number>(10);
  const [clickCrit, setClickCrit] = useState<number>(20);
  const [impWarn, setImpWarn] = useState<number>(20);
  const [posDrop, setPosDrop] = useState<number>(3.0);
  const [minClicks, setMinClicks] = useState<number>(5);
  const [minImps, setMinImps] = useState<number>(25);

  const [saving, setSaving] = useState(false);
  const [savedNotice, setSavedNotice] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    api.getAlertSettings()
      .then((data) => {
        setSettings(data);
        setClickWarn(data.click_warning_pct);
        setClickCrit(data.click_critical_pct);
        setImpWarn(data.impression_warning_pct);
        setPosDrop(data.position_drop_warning);
        setMinClicks(data.min_previous_clicks);
        setMinImps(data.min_previous_impressions);
      })
      .catch((err) => console.error(err));
  }, []);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isManager) return;
    setSaving(true);
    setSaveError(null);
    setSavedNotice(false);

    try {
      const updated = await api.updateAlertSettings({
        click_warning_pct: clickWarn,
        click_critical_pct: clickCrit,
        impression_warning_pct: impWarn,
        position_drop_warning: posDrop,
        min_previous_clicks: minClicks,
        min_previous_impressions: minImps,
      });
      setSettings(updated);
      setSavedNotice(true);
      setTimeout(() => setSavedNotice(false), 3000);
    } catch (err: any) {
      setSaveError(err.message || 'Failed to update alert settings.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
          <Settings className="w-6 h-6 text-indigo-400" />
          <span>Application & Alert Settings</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Manage notification thresholds, noise filters, and background synchronization schedules.
        </p>
      </div>

      {/* Account Profile Card */}
      <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 shadow-xl">
        <h2 className="text-base font-bold text-white mb-4 flex items-center space-x-2">
          <UserCheck className="w-5 h-5 text-indigo-400" />
          <span>Account Profile</span>
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-slate-500 block text-[11px] mb-1">Full Name</span>
            <span className="font-semibold text-white text-sm">{user?.full_name}</span>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-slate-500 block text-[11px] mb-1">Work Email</span>
            <span className="font-semibold text-white text-sm">{user?.email}</span>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-slate-500 block text-[11px] mb-1">Role & Permissions</span>
            <span className="inline-flex px-2 py-0.5 rounded-full font-bold text-[11px] bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
              {role === 'MANAGER' ? 'Manager (Full Access)' : 'Team Leader'}
            </span>
          </div>
        </div>
      </div>

      {/* Alert Thresholds Configuration */}
      <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Sliders className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-bold text-white">Alert Sensitivity & Thresholds</h2>
          </div>
          {!isManager && (
            <span className="text-[11px] text-amber-400 font-semibold bg-amber-500/10 px-2.5 py-1 rounded-lg border border-amber-500/20">
              Read-Only for Team Leaders
            </span>
          )}
        </div>
        <p className="text-xs text-slate-400 mb-6">
          Alerts evaluate automatically during synchronization runs comparing the latest 28 complete days against the preceding 28 complete days.
        </p>

        {savedNotice && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Alert thresholds updated successfully!</span>
          </div>
        )}

        {saveError && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{saveError}</span>
          </div>
        )}

        <form onSubmit={handleSaveSettings} className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Click Warning */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <label className="block text-xs font-semibold text-slate-200 mb-1">
                Click Decline Warning (%)
              </label>
              <p className="text-[11px] text-slate-400 mb-2">Triggers a WARNING alert when clicks drop by this percentage.</p>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  disabled={!isManager}
                  value={clickWarn}
                  onChange={(e) => setClickWarn(Number(e.target.value))}
                  min={1}
                  max={100}
                  className="w-24 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs font-bold focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                />
                <span className="text-xs text-slate-400">% decline</span>
              </div>
            </div>

            {/* Click Critical */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <label className="block text-xs font-semibold text-slate-200 mb-1">
                Click Decline Critical (%)
              </label>
              <p className="text-[11px] text-slate-400 mb-2">Triggers a CRITICAL alert when clicks drop by this percentage.</p>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  disabled={!isManager}
                  value={clickCrit}
                  onChange={(e) => setClickCrit(Number(e.target.value))}
                  min={1}
                  max={100}
                  className="w-24 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs font-bold focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                />
                <span className="text-xs text-slate-400">% decline</span>
              </div>
            </div>

            {/* Impression Warning */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <label className="block text-xs font-semibold text-slate-200 mb-1">
                Visibility / Impression Drop Warning (%)
              </label>
              <p className="text-[11px] text-slate-400 mb-2">Triggers when total impressions drop by this percentage.</p>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  disabled={!isManager}
                  value={impWarn}
                  onChange={(e) => setImpWarn(Number(e.target.value))}
                  min={1}
                  max={100}
                  className="w-24 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs font-bold focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                />
                <span className="text-xs text-slate-400">% decline</span>
              </div>
            </div>

            {/* Position Drop Warning */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <label className="block text-xs font-semibold text-slate-200 mb-1">
                Ranking Loss Warning (Positions)
              </label>
              <p className="text-[11px] text-slate-400 mb-2">Triggers when weighted avg rank worsens by this many spots.</p>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  step="0.5"
                  disabled={!isManager}
                  value={posDrop}
                  onChange={(e) => setPosDrop(Number(e.target.value))}
                  min={0.5}
                  max={50}
                  className="w-24 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs font-bold focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                />
                <span className="text-xs text-slate-400">positions lost</span>
              </div>
            </div>
          </div>

          {/* Noise Reduction Thresholds */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
            <h3 className="text-xs font-bold text-indigo-300 uppercase tracking-wider mb-2">
              Noise Reduction Filters
            </h3>
            <p className="text-[11px] text-slate-400 mb-3">
              Prevents noisy false-positive alerts on low-traffic pages (e.g., 2 clicks dropping to 0 clicks).
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-300 mb-1">Min Previous Clicks Required</label>
                <input
                  type="number"
                  disabled={!isManager}
                  value={minClicks}
                  onChange={(e) => setMinClicks(Number(e.target.value))}
                  min={1}
                  className="w-24 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs font-bold disabled:opacity-50"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-300 mb-1">Min Previous Impressions Required</label>
                <input
                  type="number"
                  disabled={!isManager}
                  value={minImps}
                  onChange={(e) => setMinImps(Number(e.target.value))}
                  min={1}
                  className="w-24 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs font-bold disabled:opacity-50"
                />
              </div>
            </div>
          </div>

          {isManager && (
            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={saving}
                className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-all disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                <span>{saving ? 'Updating...' : 'Save Configuration'}</span>
              </button>
            </div>
          )}
        </form>
      </div>

      {/* Scheduler Info */}
      <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 shadow-xl flex items-center justify-between">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Daily Background Synchronization Schedule</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Runs automatically once daily at <span className="text-slate-200 font-semibold">03:00 AM UTC</span> via APScheduler.
            </p>
          </div>
        </div>
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
          Enabled & Active
        </span>
      </div>

      {/* Danger Zone: Data Management */}
      {isManager && (
        <div className="bg-slate-900/90 rounded-2xl p-6 border border-rose-500/20 shadow-xl">
          <h2 className="text-base font-bold text-white mb-2 flex items-center space-x-2 text-rose-400">
            <AlertTriangle className="w-5 h-5" />
            <span>Workspace Data Management</span>
          </h2>
          <p className="text-xs text-slate-400 leading-relaxed mb-4">
            Manage demonstration data or perform a clean reset of the workspace when ready to connect real Google Search Console properties.
          </p>

          <div className="flex flex-col sm:flex-row gap-3">
            <button
              type="button"
              onClick={async () => {
                if (!window.confirm("Remove all synthetic demonstration test data (demo properties, fake metrics, demo categories, demo team leaders)?")) return;
                try {
                  const res = await api.purgeDemoData();
                  alert(res.message || "Demo data purged successfully!");
                  window.location.reload();
                } catch (e: any) {
                  alert(e.message);
                }
              }}
              className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-rose-500/15 text-slate-300 hover:text-rose-400 border border-slate-700 hover:border-rose-500/30 text-xs font-semibold transition flex items-center justify-center space-x-2"
            >
              <Trash2 className="w-4 h-4" />
              <span>Remove Demo Test Data</span>
            </button>

            <button
              type="button"
              onClick={async () => {
                if (!window.confirm("CAUTION: This will wipe ALL categories, pages, properties, and metrics across the entire workspace to give you a 100% clean slate for your own real data. Your Manager account will remain active. Continue?")) return;
                try {
                  const res = await api.resetWorkspaceData();
                  alert(res.message || "Workspace reset successfully!");
                  window.location.href = "/gsc-connection";
                } catch (e: any) {
                  alert(e.message);
                }
              }}
              className="px-4 py-2.5 rounded-xl bg-rose-600/20 hover:bg-rose-600 text-rose-300 hover:text-white border border-rose-500/40 text-xs font-semibold transition flex items-center justify-center space-x-2"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Reset Entire Workspace (Clean Slate)</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
