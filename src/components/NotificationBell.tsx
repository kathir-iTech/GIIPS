import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Bell } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { AppNotification } from '../types';
import './NotificationBell.css';

const POLL_INTERVAL = 45000;

function formatRelativeTime(iso: string, t: (key: string, opts?: any) => string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return t('notification.justNow');
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return t('notification.minutesAgo', { count: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t('notification.hoursAgo', { count: hours });
  const days = Math.floor(hours / 24);
  return t('notification.daysAgo', { count: days });
}

function getNotificationMessage(n: AppNotification, t: (key: string, opts?: any) => string): string {
  const statusLabels: Record<string, string> = {
    'open': t('common.status.open'),
    'in-progress': t('common.status.inProgress'),
    'resolved': t('common.status.resolved'),
    'pending_verification': t('common.status.pendingVerification'),
  };

  switch (n.type) {
    case 'status_change': {
      const status = n.data?.new_status ? statusLabels[n.data.new_status] || n.data.new_status : '';
      return t('notification.statusChanged', { status });
    }
    case 'merged':
      return t('notification.merged', { incidentNumber: n.data?.incident_number || '' });
    case 'split':
      return t('notification.split', { incidentNumber: n.data?.incident_number || '' });
    case 'created':
      return t('notification.created', { incidentNumber: n.data?.incident_number || '' });
    case 'complaint_assigned':
      return t('notification.complaintAssigned', { incidentNumber: n.data?.incident_number || '' });
    case 'pending_verification':
      return t('notification.pendingVerification', { incidentNumber: n.data?.incident_number || '' });
    case 'aging_warning':
      return t('notification.agingWarning', { incidentNumber: n.data?.incident_number || '', days: n.data?.days_open || '' });
    case 'aging_critical':
      return t('notification.agingCritical', { incidentNumber: n.data?.incident_number || '', days: n.data?.days_open || '' });
    case 'officer_merged':
      return t('notification.officerMerged', { incidentNumber: n.data?.incident_number || '' });
    case 'officer_split':
      return t('notification.officerSplit', { incidentNumber: n.data?.incident_number_orig || '', incidentNumberNew: n.data?.incident_number_new || '' });
    case 'officer_status_change':
      return t('notification.officerStatusChange', { incidentNumber: n.data?.incident_number || '', newStatus: t(`common.status.${n.data?.new_status || 'open'}`) });
    default:
      return '';
  }
}

export default function NotificationBell() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const fetchNotifications = useCallback(async () => {
    if (!user || !['Citizen', 'Officer', 'Executive'].includes(user.role)) return;
    try {
      const data = await api.getNotifications();
      setNotifications(data);
    } catch {
      // silently fail
    }
  }, [user]);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // silently fail
    }
  };

  const handleClick = async (n: AppNotification) => {
    if (!n.is_read) {
      try {
        await api.markNotificationRead(n.id);
        setNotifications((prev) =>
          prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x))
        );
      } catch {
        // silently fail
      }
    }
    if (n.complaint_id) {
      navigate(`/complaint/${n.complaint_id}`);
    }
    setOpen(false);
  };

  if (!user || !['Citizen', 'Officer', 'Executive'].includes(user.role)) return null;

  return (
    <div className="notification-bell" ref={ref}>
      <button className="bell-btn" onClick={() => setOpen(!open)} aria-label={t('notification.title')}>
        <Bell size={20} />
        {unreadCount > 0 && <span className="badge">{unreadCount > 99 ? '99+' : unreadCount}</span>}
      </button>

      {open && (
        <div className="notification-dropdown">
          <div className="dropdown-header">
            <span>{t('notification.title')}</span>
            {unreadCount > 0 && (
              <button className="mark-all-btn" onClick={handleMarkAllRead}>
                {t('notification.markAllRead')}
              </button>
            )}
          </div>
          <div className="dropdown-body">
            {notifications.length === 0 ? (
              <div className="empty-state">{t('notification.empty')}</div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={`notification-item ${n.is_read ? 'read' : 'unread'}`}
                  onClick={() => handleClick(n)}
                >
                  <div className="notif-msg">{getNotificationMessage(n, t)}</div>
                  <div className="notif-time">{formatRelativeTime(n.created_at, t)}</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
