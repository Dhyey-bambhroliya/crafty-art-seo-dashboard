import React, { useState, useEffect } from 'react';
import { RefreshCw, Globe, Calendar, AlertCircle, Database, CheckCircle2 } from 'lucide-react';
import { api } from '../../services/api';
import { GSCProperty } from '../../types';
import { useAuth } from '../../context/AuthContext';

interface HeaderProps {
  latestDataDate?: string;
  isDemoData?: boolean;
  onSyncCompleted?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  latestDataDate,
  onSyncCompleted
}) => {
  const { role } = useAuth();
  const isManager = role === 'MANAGER';
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [activeProperty, setActiveProperty] = useState<GSCProperty | null>(null);

  const loadActiveProperty = async () => {
    try {
      const props = await api.getGscProperties();
      const active = props.find(p => p.is_active) || props[0] || null;
      setActiveProperty(active);
    } catch (e) {
      console.error(e);
      setActiveProperty(null);
    }
  };

  useEffect(() => {
    loadActiveProperty();
    window.addEventListener('gsc-property-changed', loadActiveProperty);
    return () => window.removeEventListener('gsc-property-changed', loadActiveProperty);
  }, []);

  const handleManualSync = async () => {
    if (syncing) return;
    setSyncing(true);
    setSyncMessage(null);
    try {
      if (!activeProperty) {
        setSyncMessage('No property connected. Please connect a Search Console property.');
        return;
      }
      const res = await api.triggerSync(activeProperty.id);
      setSyncMessage(res.message || 'Sync started in background!');
      if (onSyncCompleted) onSyncCompleted();
    } catch (err: any) {
      setSyncMessage(`Sync error: ${err.message}`);
    } finally {
      setSyncing(false);
      setTimeout(() => setSyncMessage(null), 5000);
    }
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-30 px-6 flex items-center justify-between">
      {/* Left: Active Property & Demo Indicator */}
      <div className="flex items-center space-x-3">
        {activeProperty ? (
          <>
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs">
              <Globe className="w-3.5 h-3.5 text-indigo-400" />
              <span className="font-medium text-slate-300">Property:</span>
              <span className="font-semibold text-white">{activeProperty.site_url}</span>
            </div>

            {activeProperty.is_demo && (
              <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-semibold" title="Synthetic development data is currently active">
                <Database className="w-3.5 h-3.5 text-amber-400" />
                <span>[DEMO DATA ACTIVE]</span>
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-400">
            <Globe className="w-3.5 h-3.5 text-slate-500" />
            <span>No Search Console Property Connected</span>
          </div>
        )}
      </div>

      {/* Right: Freshness & Actions */}
      <div className="flex items-center space-x-4">
        {latestDataDate && (
          <div className="hidden sm:flex items-center space-x-2 text-xs text-slate-400 bg-slate-950/40 px-3 py-1.5 rounded-lg border border-slate-800">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span>Latest GSC Data:</span>
            <span className="font-semibold text-slate-200">{latestDataDate}</span>
          </div>
        )}

        {syncMessage && (
          <span className={`text-xs px-2.5 py-1 rounded-md flex items-center space-x-1 ${
            syncMessage.includes('error') ? 'bg-red-500/15 text-red-300' : 'bg-emerald-500/15 text-emerald-300'
          }`}>
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{syncMessage}</span>
          </span>
        )}

        {isManager && (
          <button
            onClick={handleManualSync}
            disabled={syncing}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
            title="Fetch latest page metrics from Google Search Console"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
            <span>{syncing ? 'Syncing...' : 'Sync GSC Now'}</span>
          </button>
        )}
      </div>
    </header>
  );
};
