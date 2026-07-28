import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import Header from '../components/Header';
import { CheckCircle, Clock, AlertTriangle, GitMerge, GitBranch, Bell, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './Notifications.css';

interface Notification {
  id: string; type: string; message: string; created_at: string; is_read: boolean; complaint_id?: string;
}

const TIMELINE_ICONS: Record<string, any> = {
  status_change: Clock, merged: GitMerge, split: GitBranch, created: CheckCircle,
  complaint_assigned: Bell, pending_verification: AlertTriangle,
};

const Notifications = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getNotifications().then(setNotifications).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const markAllRead = async () => {
    await api.markAllNotificationsRead();
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
  };

  const groupByDate = (notifs: Notification[]) => {
    const groups: Record<string, Notification[]> = {};
    notifs.forEach(n => {
      const date = new Date(n.created_at).toLocaleDateString();
      if (!groups[date]) groups[date] = [];
      groups[date].push(n);
    });
    return groups;
  };

  return (
    <div className="notifications-page">
      <Header title="Notifications" subtitle="Your notification history" />
      <div className="notif-controls">
        <button className="back-btn" onClick={() => navigate(-1)}><ArrowLeft size={16} /> Back</button>
        <button className="mark-all-btn" onClick={markAllRead}>Mark all read</button>
      </div>
      <div className="notif-timeline">
        {loading ? <div className="loading">Loading...</div> : notifications.length === 0 ? (
          <div className="empty">No notifications yet</div>
        ) : Object.entries(groupByDate(notifications)).map(([date, notifs]) => (
          <div key={date} className="notif-date-group">
            <h3 className="notif-date-header">{date}</h3>
            {notifs.map(n => {
              const Icon = TIMELINE_ICONS[n.type] || Bell;
              return (
                <div key={n.id} className={`notif-item ${!n.is_read ? 'unread' : ''}`}
                  onClick={() => n.complaint_id && navigate(`/complaint/${n.complaint_id}`)}>
                  <div className="notif-icon"><Icon size={16} /></div>
                  <div className="notif-body">
                    <p>{n.message}</p>
                    <span className="notif-time">{new Date(n.created_at).toLocaleTimeString()}</span>
                  </div>
                  {!n.is_read && <div className="notif-unread-dot" />}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};
export default Notifications;
