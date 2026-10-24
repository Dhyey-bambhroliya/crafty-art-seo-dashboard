import React, { useState, useEffect } from 'react';
import { History, CheckCircle2, XCircle, Clock, RefreshCw, Calendar, Database } from 'lucide-react';
import { api } from '../services/api';
import { SyncRun } from '../types';

export const SyncHistoryPage: React.FC = () => {
  const [runs, setRuns] = useState<SyncRun[]>([]);
  const [loading, setLoading] = useState(true);

  const loadRuns = async () => {
    setLoading(true);
    try {
      const data = await api.getSyncRuns();
      setRuns(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
            <History className="w-6 h-6 text-indigo-400" />
            <span>Search Console Synchronization Logs</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Audit history of scheduled background jobs and manual GSC ingestion runs.
          </p>
        </div>

        <button
          onClick={loadRuns}
          className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors"
          title="Refresh sync runs"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Sync Runs Table */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-xl shadow-black/20">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-6">Status</th>
                <th className="py-3.5 px-4">Property</th>
                <th className="py-3.5 px-4">Triggered By</th>
                <th className="py-3.5 px-4">Pages Synced</th>
                <th className="py-3.5 px-4">Records Created</th>
                <th className="py-3.5 px-4">Alerts Evaluated</th>
                <th className="py-3.5 px-4">Data Cutoff Date</th>
                <th className="py-3.5 px-6">Execution Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {runs.map((r) => {
                const isSuccess = r.status === 'SUCCESS';
                const isFailed = r.status === 'FAILED';

                return (
                  <tr key={r.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-4 px-6">
                      {isSuccess ? (
                        <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>SUCCESS</span>
                        </span>
                      ) : isFailed ? (
                        <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                          <XCircle className="w-3.5 h-3.5" />
                          <span>FAILED</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30 animate-pulse">
                          <Clock className="w-3.5 h-3.5" />
                          <span>RUNNING</span>
                        </span>
                      )}
                    </td>

                    <td className="py-4 px-4 font-semibold text-white truncate max-w-xs">
                      {r.property_site_url || 'sc-domain:craftyartapp.com'}
                    </td>

                    <td className="py-4 px-4 text-slate-400 font-medium">
                      {r.triggered_by}
                    </td>

                    <td className="py-4 px-4 font-bold text-slate-200">
                      {r.pages_synced}
                    </td>

                    <td className="py-4 px-4 font-bold text-slate-200">
                      {r.records_created.toLocaleString()}
                    </td>

                    <td className="py-4 px-4 font-semibold text-indigo-400">
                      {r.alerts_generated} alert(s)
                    </td>

                    <td className="py-4 px-4 text-slate-400 font-medium">
                      {r.latest_data_date || 'N/A'}
                    </td>

                    <td className="py-4 px-6 text-slate-400">
                      <div>{new Date(r.start_time).toLocaleTimeString()}</div>
                      <div className="text-[10px] text-slate-500">{new Date(r.start_time).toLocaleDateString()}</div>
                    </td>
                  </tr>
                );
              })}

              {runs.length === 0 && !loading && (
                <tr>
                  <td colSpan={8} className="py-10 text-center text-slate-500">
                    No sync run logs recorded yet.
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
