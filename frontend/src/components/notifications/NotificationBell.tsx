import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell, Check, CheckCheck, Clock, Calendar, AlertTriangle,
  ExternalLink, Sparkles, X, ShieldAlert
} from 'lucide-react';
import { festivalApi } from '../../services/festivalApi';
import { FestivalNotification } from '../../types/festival';

export const NotificationBell: React.FC = () => {
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [notifications, setNotifications] = useState<FestivalNotification[]>([]);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Load unread count periodically
  const fetchUnreadCount = async () => {
    try {
      const res = await festivalApi.getUnreadNotificationCount();
      setUnreadCount(res.unread_count);
    } catch (e) {
      console.error('Failed to fetch unread notification count', e);
    }
  };

  // Load notification items when opened
  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const items = await festivalApi.getNotifications(undefined, 25, 0);
      setNotifications(items);
    } catch (e) {
      console.error('Failed to fetch notifications', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleMarkAsRead = async (id: number, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      await festivalApi.markNotificationAsRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (e) {
      console.error('Failed to mark notification read', e);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await festivalApi.markAllNotificationsAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (e) {
      console.error('Failed to mark all notifications read', e);
    }
  };

  const handleNotificationClick = async (notif: FestivalNotification) => {
    if (!notif.is_read) {
      await handleMarkAsRead(notif.id);
    }
    setIsOpen(false);
    if (notif.action_url) {
      navigate(notif.action_url);
    } else if (notif.festival_id) {
      navigate(`/festivals/${notif.festival_id}`);
    }
  };

  const getNotificationIcon = (type: string) => {
    if (type.includes('30_DAY') || type.includes('15_DAY') || type.includes('7_DAY')) {
      return <Clock className="w-4 h-4 text-indigo-400" />;
    }
    if (type.includes('OVERDUE')) {
      return <AlertTriangle className="w-4 h-4 text-rose-400" />;
    }
    if (type.includes('DECLINE')) {
      return <ShieldAlert className="w-4 h-4 text-amber-400" />;
    }
    if (type.includes('APPROVAL')) {
      return <Sparkles className="w-4 h-4 text-emerald-400" />;
    }
    return <Calendar className="w-4 h-4 text-blue-400" />;
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
        title="Festival Milestone Notifications & Reminders"
        aria-label="Festival Notifications"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-rose-500 rounded-full shadow-lg shadow-rose-500/50 animate-pulse">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 max-w-[calc(100vw-2rem)] rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl shadow-black/80 z-50 overflow-hidden flex flex-col">
          {/* Header */}
          <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
            <div className="flex items-center space-x-2">
              <Bell className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-semibold text-white">Festival Notifications</h3>
              {unreadCount > 0 && (
                <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                  {unreadCount} unread
                </span>
              )}
            </div>

            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="flex items-center space-x-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors font-medium"
                title="Mark all notifications as read"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                <span>Mark all read</span>
              </button>
            )}
          </div>

          {/* Notification List */}
          <div className="max-h-96 overflow-y-auto divide-y divide-slate-800/60">
            {loading ? (
              <div className="p-8 text-center text-slate-500 flex flex-col items-center justify-center space-y-2">
                <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-xs">Loading notifications...</span>
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-500 flex flex-col items-center justify-center space-y-2">
                <div className="w-10 h-10 rounded-full bg-slate-800/80 flex items-center justify-center text-slate-400">
                  <Bell className="w-5 h-5" />
                </div>
                <p className="text-xs font-medium text-slate-400">No notifications yet</p>
                <p className="text-[11px] text-slate-600">You're all caught up on festival milestones and preparation tasks.</p>
              </div>
            ) : (
              notifications.map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif)}
                  className={`p-3.5 transition-colors cursor-pointer flex items-start space-x-3 hover:bg-slate-800/60 ${
                    !notif.is_read ? 'bg-indigo-950/20' : 'bg-transparent'
                  }`}
                >
                  <div className="mt-0.5 p-2 rounded-xl bg-slate-800 border border-slate-700/60 shrink-0">
                    {getNotificationIcon(notif.notification_type)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className={`text-xs font-semibold truncate ${!notif.is_read ? 'text-white' : 'text-slate-300'}`}>
                        {notif.title}
                      </p>
                      {!notif.is_read && (
                        <button
                          onClick={(e) => handleMarkAsRead(notif.id, e)}
                          className="ml-2 text-slate-400 hover:text-indigo-400 p-1 rounded-md transition-colors"
                          title="Mark as read"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>

                    <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                      {notif.message}
                    </p>

                    <div className="flex items-center space-x-2 mt-2 text-[10px] text-slate-500 font-medium">
                      <span>{new Date(notif.created_at).toLocaleDateString()}</span>
                      {notif.festival_name && (
                        <>
                          <span>•</span>
                          <span className="text-indigo-400">{notif.festival_name}</span>
                        </>
                      )}
                      {notif.action_url && (
                        <>
                          <span>•</span>
                          <span className="flex items-center space-x-0.5 text-slate-400">
                            <span>View</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2.5 border-t border-slate-800 bg-slate-950/60 text-center">
            <span className="text-[11px] text-slate-500 font-medium">
              Dashboard-only milestone alerts & task updates
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
