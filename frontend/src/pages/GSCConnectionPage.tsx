import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Globe, ShieldCheck, RefreshCw, CheckCircle2, AlertCircle,
  Database, ExternalLink, KeyRound, Sparkles, Settings, Save, Info, X, Trash2
} from 'lucide-react';
import { api } from '../services/api';
import { GSCProperty, GSCConfigStatus } from '../types';
import { useAuth } from '../context/AuthContext';

export const GSCConnectionPage: React.FC = () => {
  const { role } = useAuth();
  const isManager = role === 'MANAGER';
  const location = useLocation();
  const navigate = useNavigate();

  const [properties, setProperties] = useState<GSCProperty[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [syncingId, setSyncingId] = useState<number | null>(null);
  const [notice, setNotice] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // GSC OAuth credentials status
  const [configStatus, setConfigStatus] = useState<GSCConfigStatus | null>(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showPurgeModal, setShowPurgeModal] = useState(false);
  const [showManualModal, setShowManualModal] = useState(false);
  const [manualSiteUrl, setManualSiteUrl] = useState('');
  const [savingManual, setSavingManual] = useState(false);
  const [purging, setPurging] = useState(false);
  const [clientIdInput, setClientIdInput] = useState('');
  const [clientSecretInput, setClientSecretInput] = useState('');
  const [savingConfig, setSavingConfig] = useState(false);

  const loadProperties = async () => {
    setLoading(true);
    try {
      const data = await api.getGscProperties();
      setProperties(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadConfigStatus = async () => {
    try {
      const status = await api.getGscConfigStatus();
      setConfigStatus(status);
    } catch (err: any) {
      console.error('Failed to load GSC config status:', err);
    }
  };

  const exchangedCodeRef = React.useRef<string | null>(null);

  // Handle OAuth code return from Google if redirected back here
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const code = params.get('code');
    if (code && isManager) {
      if (exchangedCodeRef.current === code) return;
      exchangedCodeRef.current = code;

      // Clean dead code from browser address bar immediately so refresh won't replay it
      window.history.replaceState({}, document.title, window.location.pathname);

      setConnecting(true);
      const redirectUri = window.location.origin + '/gsc-connection';
      api.exchangeGscCode(code, redirectUri)
        .then((res) => {
          setNotice({ type: 'success', text: res.message || 'Google Search Console connected successfully!' });
          loadProperties();
          loadConfigStatus();
        })
        .catch((err) => {
          setNotice({ 
            type: 'error', 
            text: err.message || 'Authorization expired or invalid. Please click Authorize with Google again.' 
          });
        })
        .finally(() => setConnecting(false));
    } else {
      loadProperties();
      loadConfigStatus();
    }
  }, [location.search, isManager]);

  const handleStartOAuth = async () => {
    if (configStatus && (!configStatus.client_id_configured || !configStatus.client_secret_configured)) {
      setShowConfigModal(true);
      setNotice({
        type: 'info',
        text: 'Please configure your Google Cloud OAuth Client ID & Secret below, or use the Demo Dataset.'
      });
      return;
    }

    setConnecting(true);
    setNotice(null);
    try {
      const redirectUri = window.location.origin + '/gsc-connection';
      const { auth_url } = await api.getGscAuthUrl(redirectUri);
      window.location.href = auth_url;
    } catch (err: any) {
      if (err.message && err.message.toLowerCase().includes('not configured')) {
        setShowConfigModal(true);
        setNotice({
          type: 'info',
          text: 'Google OAuth Client ID & Secret are required. Enter them below or continue using Demo Dataset.'
        });
      } else {
        setNotice({
          type: 'error',
          text: err.message || 'Ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are configured.'
        });
      }
      setConnecting(false);
    }
  };

  const handleSaveCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientIdInput.trim() || !clientSecretInput.trim()) {
      setNotice({ type: 'error', text: 'Both Client ID and Client Secret are required.' });
      return;
    }

    if (clientIdInput.includes('@') && !clientIdInput.includes('.apps.googleusercontent.com')) {
      setNotice({
        type: 'error',
        text: 'Invalid Client ID: Google Client ID must be an OAuth 2.0 Web Client ID from Google Cloud Console (e.g. 123456-xxx.apps.googleusercontent.com), not an email address.'
      });
      return;
    }

    setSavingConfig(true);
    try {
      const res = await api.updateGscConfig({
        client_id: clientIdInput.trim(),
        client_secret: clientSecretInput.trim(),
      });
      setConfigStatus(res);
      setShowConfigModal(false);
      setNotice({
        type: 'success',
        text: 'Google OAuth credentials saved successfully! You can now authorize with Google.'
      });
      setClientIdInput('');
      setClientSecretInput('');
    } catch (err: any) {
      setNotice({ type: 'error', text: err.message || 'Failed to save Google credentials.' });
    } finally {
      setSavingConfig(false);
    }
  };

  const handleSaveManualProperty = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualSiteUrl.trim()) return;
    setSavingManual(true);
    try {
      await api.addPropertyManually({ site_url: manualSiteUrl.trim(), permission_level: 'siteOwner' });
      setShowManualModal(false);
      setManualSiteUrl('');
      window.dispatchEvent(new Event('gsc-property-changed'));
      setNotice({ type: 'success', text: `Property '${manualSiteUrl.trim()}' connected successfully! You can now map category URLs.` });
      loadProperties();
    } catch (err: any) {
      setNotice({ type: 'error', text: err.message || 'Failed to connect property.' });
    } finally {
      setSavingManual(false);
    }
  };

  const handleManualSync = async (propertyId: number) => {
    setSyncingId(propertyId);
    setNotice(null);
    try {
      const res = await api.triggerSync(propertyId);
      setNotice({ 
        type: 'success', 
        text: res.message || 'Synchronization started in background. Your Search Console metrics are now being ingested.' 
      });
      setTimeout(loadProperties, 4000);
      setTimeout(loadProperties, 10000);
    } catch (err: any) {
      setNotice({ type: 'error', text: `Sync failed: ${err.message}` });
    } finally {
      setSyncingId(null);
    }
  };

  const handleSeedDemoData = async () => {
    setConnecting(true);
    setNotice(null);
    try {
      await api.seedDemoData();
      setNotice({ type: 'success', text: 'Realistic Crafty Art demo dataset loaded successfully with 56 days of metrics!' });
      window.dispatchEvent(new Event('gsc-property-changed'));
      loadProperties();
    } catch (err: any) {
      setNotice({ type: 'error', text: err.message });
    } finally {
      setConnecting(false);
    }
  };

  const handlePurgeDemoData = () => {
    setShowPurgeModal(true);
  };

  const confirmPurgeDemoData = async () => {
    setPurging(true);
    setNotice(null);
    try {
      const res = await api.purgeDemoData();
      setShowPurgeModal(false);
      setNotice({
        type: 'success',
        text: res.message || 'Demo test data purged successfully! The system is now ready for your own real data.'
      });
      window.dispatchEvent(new Event('gsc-property-changed'));
      loadProperties();
    } catch (err: any) {
      setNotice({ type: 'error', text: err.message || 'Failed to purge demo data.' });
    } finally {
      setPurging(false);
    }
  };

  const handleDeleteProperty = async (prop: GSCProperty) => {
    if (!window.confirm(`Are you sure you want to disconnect and delete property '${prop.site_url}' and all associated daily metrics?`)) {
      return;
    }
    try {
      await api.deleteGscProperty(prop.id);
      window.dispatchEvent(new Event('gsc-property-changed'));
      setNotice({ type: 'success', text: `Property '${prop.site_url}' deleted successfully.` });
      loadProperties();
    } catch (err: any) {
      setNotice({ type: 'error', text: err.message || 'Failed to delete property.' });
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
          <Globe className="w-6 h-6 text-indigo-400" />
          <span>Google Search Console Integration</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Secure OAuth 2.0 connection using read-only Search Console scope to ingest daily page clicks, impressions, CTR, and rankings.
        </p>
      </div>

      {notice && (
        <div
          className={`p-4 rounded-xl border text-xs flex items-center justify-between space-x-3 ${
            notice.type === 'success'
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
              : notice.type === 'info'
              ? 'bg-indigo-500/15 border-indigo-500/30 text-indigo-300'
              : 'bg-rose-500/15 border-rose-500/30 text-rose-300'
          }`}
        >
          <div className="flex items-center space-x-3">
            {notice.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            ) : notice.type === 'info' ? (
              <Info className="w-4 h-4 shrink-0 text-indigo-400" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            )}
            <span>{notice.text}</span>
          </div>
          <button
            onClick={() => setNotice(null)}
            className="p-1 hover:bg-white/10 rounded text-slate-400 hover:text-white"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Connection Actions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Real GSC OAuth Card */}
        <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <KeyRound className="w-5 h-5" />
              </div>
              <div className="flex items-center space-x-2">
                {configStatus && (
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                      configStatus.client_id_configured
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                        : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                    }`}
                  >
                    {configStatus.client_id_configured ? 'Credentials Ready' : 'Credentials Missing'}
                  </span>
                )}
                {isManager && (
                  <button
                    onClick={() => setShowConfigModal(true)}
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition"
                    title="Configure Google OAuth Credentials"
                  >
                    <Settings className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
            <h2 className="text-base font-bold text-white mb-2">Connect Google Search Console</h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              Connect your verified Google account to automatically sync daily page metrics for Crafty Art. Uses the official read-only scope:
            </p>
            <code className="text-[11px] block mt-2 bg-slate-950 p-2 rounded-lg text-indigo-300 border border-slate-800 break-all font-mono">
              https://www.googleapis.com/auth/webmasters.readonly
            </code>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800 space-y-2">
            {isManager ? (
              <>
                <button
                  onClick={handleStartOAuth}
                  disabled={connecting}
                  className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  <Globe className="w-4 h-4" />
                  <span>{connecting ? 'Redirecting to Google...' : 'Authorize with Google'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setShowManualModal(true)}
                  className="w-full py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition flex items-center justify-center space-x-1.5"
                >
                  <Globe className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Directly Connect Property URL (Manual)</span>
                </button>
                {configStatus && !configStatus.client_id_configured && (
                  <button
                    onClick={() => setShowConfigModal(true)}
                    className="w-full py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition flex items-center justify-center space-x-1.5"
                  >
                    <Settings className="w-3.5 h-3.5" />
                    <span>Enter Google OAuth Client ID & Secret</span>
                  </button>
                )}
              </>
            ) : (
              <p className="text-xs text-slate-500">Only Managers can authorize new Search Console accounts.</p>
            )}
          </div>
        </div>

        {/* Demo Mode / Synthetic Seed Card */}
        <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                <Database className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider">
                Development & Demo Mode
              </span>
            </div>
            <h2 className="text-base font-bold text-white mb-2">Crafty Art Demonstration Dataset</h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              Instantly populate or refresh realistic Crafty Art Search Console data (56 days of daily metrics, 4 categories, 2 team leaders, and simulated traffic decline alerts).
            </p>
            <div className="mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px]">
              Tagged explicitly as <span className="font-mono font-bold">[DEMO DATA]</span> to prevent any confusion with production metrics.
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800 space-y-2">
            {isManager ? (
              <>
                <button
                  onClick={handleSeedDemoData}
                  disabled={connecting}
                  className="w-full py-2.5 px-4 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-lg shadow-amber-600/25 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Reload Demo Dataset</span>
                </button>
                <button
                  onClick={handlePurgeDemoData}
                  disabled={connecting}
                  className="w-full py-2 px-4 rounded-xl bg-slate-800 hover:bg-rose-500/15 text-slate-300 hover:text-rose-400 border border-slate-700 hover:border-rose-500/30 text-xs font-medium transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Remove Test / Demo Data</span>
                </button>
              </>
            ) : (
              <p className="text-xs text-slate-500">Demo dataset active for read-only inspection.</p>
            )}
          </div>
        </div>
      </div>

      {/* OAuth Credentials Configuration Modal */}
      {showConfigModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                  <KeyRound className="w-4 h-4" />
                </div>
                <h3 className="text-base font-bold text-white">Google OAuth Credentials</h3>
              </div>
              <button
                onClick={() => setShowConfigModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              To connect real Search Console properties, create OAuth 2.0 Web Application credentials in your{' '}
              <a
                href="https://console.cloud.google.com/apis/credentials"
                target="_blank"
                rel="noreferrer"
                className="text-indigo-400 underline hover:text-indigo-300 inline-flex items-center space-x-0.5"
              >
                <span>Google Cloud Console</span>
                <ExternalLink className="w-3 h-3 ml-0.5 inline" />
              </a>
              . Add Authorized Redirect URI:
            </p>

            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-emerald-400 mb-4 break-all">
              {window.location.origin}/gsc-connection
            </div>

            <form onSubmit={handleSaveCredentials} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Google Client ID <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 123456789-abcdef.apps.googleusercontent.com"
                  value={clientIdInput}
                  onChange={(e) => setClientIdInput(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Google Client Secret <span className="text-rose-400">*</span>
                </label>
                <input
                  type="password"
                  required
                  placeholder="e.g. GOCSPX-xxxxxxxxxxxxxxxx"
                  value={clientSecretInput}
                  onChange={(e) => setClientSecretInput(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowConfigModal(false);
                    handleSeedDemoData();
                  }}
                  className="text-xs text-amber-400 hover:text-amber-300 underline font-medium"
                >
                  Use Demo Mode Instead
                </button>
                <div className="flex space-x-2">
                  <button
                    type="button"
                    onClick={() => setShowConfigModal(false)}
                    className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={savingConfig}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition disabled:opacity-50 flex items-center space-x-1.5"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{savingConfig ? 'Saving...' : 'Save Credentials'}</span>
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Purge Demo Test Data Confirmation Modal */}
      {showPurgeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 shrink-0">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Remove Demo Test Data?</h3>
                <p className="text-xs text-slate-400">Clear all demonstration metrics and properties</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed mb-6">
              This will remove all 56 days of synthetic demonstration metrics, demo properties, demo categories, and test alerts.
              <br /><br />
              Your Manager account and real Google OAuth credentials will remain safe and intact.
            </p>

            <div className="flex items-center justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowPurgeModal(false)}
                disabled={purging}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmPurgeDemoData}
                disabled={purging}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-lg shadow-rose-600/25 transition flex items-center space-x-1.5 disabled:opacity-50"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{purging ? 'Removing Test Data...' : 'Yes, Remove Test Data'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manual Property Connection Modal */}
      {showManualModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                  <Globe className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Direct Property Connection</h3>
                  <p className="text-[11px] text-slate-400">Connect domain or URL prefix without Google Cloud OAuth</p>
                </div>
              </div>
              <button
                onClick={() => setShowManualModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed mb-4">
              If you want to start mapping Crafty Art categories and landing page URLs right away before setting up Google Cloud API keys, enter your Search Console site URL or domain property here.
            </p>

            <form onSubmit={handleSaveManualProperty} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Site / Domain Property URL <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. sc-domain:craftyartapp.com or https://craftyartapp.com/"
                  value={manualSiteUrl}
                  onChange={(e) => setManualSiteUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono"
                />
                <span className="block text-[10px] text-slate-500 mt-1">
                  Supports Domain property (e.g. <code className="text-indigo-400">sc-domain:craftyartapp.com</code>) or URL prefix (e.g. <code className="text-indigo-400">https://craftyartapp.com/</code>).
                </span>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowManualModal(false)}
                  disabled={savingManual}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingManual || !manualSiteUrl.trim()}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition flex items-center space-x-1.5 disabled:opacity-50"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>{savingManual ? 'Connecting...' : 'Connect Property'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Discovered & Active GSC Properties */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-xl shadow-black/20">
        <div className="p-4 border-b border-slate-800">
          <h2 className="text-base font-bold text-white tracking-tight">Active Search Console Properties</h2>
          <p className="text-xs text-slate-400">Configured properties receiving automatic daily synchronization</p>
        </div>

        <div className="divide-y divide-slate-800">
          {properties.map((prop) => (
            <div key={prop.id} className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start space-x-3.5">
                <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-0.5">
                  <Globe className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-white text-sm">{prop.site_url}</span>
                    {prop.is_demo && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-bold uppercase">
                        DEMO
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Permission: <span className="text-slate-300 font-medium">{prop.permission_level}</span> •{' '}
                    Latest Data Date: <span className="text-indigo-400 font-medium">{prop.latest_data_date || 'Pending sync'}</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3 self-end sm:self-auto">
                <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Connected</span>
                </span>

                {isManager && (
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleManualSync(prop.id)}
                      disabled={syncingId === prop.id}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors disabled:opacity-50"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${syncingId === prop.id ? 'animate-spin' : ''}`} />
                      <span>{syncingId === prop.id ? 'Syncing...' : 'Sync Now'}</span>
                    </button>
                    <button
                      onClick={() => handleDeleteProperty(prop)}
                      className="p-1.5 rounded-xl bg-slate-800 hover:bg-rose-500/15 text-slate-400 hover:text-rose-400 border border-slate-700 hover:border-rose-500/30 transition-colors"
                      title="Disconnect & Delete Property"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {properties.length === 0 && !loading && (
            <div className="p-8 text-center text-slate-500 text-xs">
              No Search Console property connected yet. Authorize your Google account or click "Reload Demo Dataset".
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
