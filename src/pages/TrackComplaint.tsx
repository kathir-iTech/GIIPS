import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { Search, ArrowLeft, CheckCircle, Clock, MapPin, Tag, Calendar, AlertTriangle, Loader2, Building2, User, Activity } from 'lucide-react';
import { StatusTimeline, useStatusStages } from '../components/StatusTimeline';
import { getDeptI18nKey } from '../data/departments';
import './TrackComplaint.css';

const STATUS_STYLES: Record<string, string> = {
  open: 'status-open',
  'in-progress': 'status-progress',
  resolved: 'status-resolved',
  pending_verification: 'status-pending-verification',
  closed: 'status-closed',
  pending: 'status-pending',
};

const STATUS_KEY: Record<string, string> = {
  open: 'common.status.open',
  'in-progress': 'common.status.inProgress',
  resolved: 'common.status.resolved',
  pending_verification: 'common.status.pendingVerification',
  closed: 'common.status.closed',
  pending: 'common.status.pending',
};

const TIMELINE_ICONS: Record<string, typeof CheckCircle> = {
  Submitted: CheckCircle,
  Categorized: CheckCircle,
  Assigned: CheckCircle,
  'In Progress': Clock,
  Resolved: CheckCircle,
  'Pending Verification': AlertTriangle,
};

const TIMELINE_COLORS: Record<string, string> = {
  Submitted: '#3b82f6',
  Categorized: '#8b5cf6',
  Assigned: '#f59e0b',
  'In Progress': '#eab308',
  Resolved: '#16a34a',
  'Pending Verification': '#ea580c',
};

const TrackComplaint = () => {
  const { t } = useTranslation();
  const [complaintId, setComplaintId] = useState('');
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTrack = async () => {
    const id = complaintId.trim();
    if (!id) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const result = await api.trackComplaint(id);
      setData(result);
    } catch (err: any) {
      setError(err.message || t('track.notFound'));
    } finally {
      setLoading(false);
    }
  };

  const statusStages = useStatusStages(
    data?.dateReceived ?? null,
    data?.status ?? 'pending',
    !!(data?.officer_name),
    !!(data?.category),
  );

  return (
    <div className="track-page">
      <div className="track-container">
        <Link to="/" className="track-back"><ArrowLeft size={16} /> {t('track.backButton')}</Link>

        <div className="track-header">
          <h1>{t('track.title')}</h1>
          <p>{t('track.subtitle')}</p>
        </div>

        <div className="track-search">
          <input
            type="text"
            className="track-input"
            placeholder={t('track.placeholder')}
            value={complaintId}
            onChange={e => setComplaintId(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleTrack(); }}
          />
          <button className="track-btn" onClick={handleTrack} disabled={loading || !complaintId.trim()}>
            {loading ? <Loader2 size={18} className="spin" /> : <Search size={18} />}
            {t('track.searchButton')}
          </button>
        </div>

        {error && <div className="track-error">{error}</div>}

        {loading && (
          <div className="track-loading">
            <Loader2 size={24} className="spin" />
            <span>{t('track.searching')}</span>
          </div>
        )}

        {data && (
          <div className="track-result">
            <div className="track-status-header">
              <h2>{data.title}</h2>
              <span className={`status-badge ${STATUS_STYLES[data.status] || 'status-pending'}`}>
                {t(STATUS_KEY[data.status] || 'common.status.pending')}
              </span>
            </div>

            <div className="track-meta">
              <div className="meta-item"><Tag size={14} /> <span>{t('track.fieldId')}: {data.complaintId}</span></div>
              <div className="meta-item"><MapPin size={14} /> <span>{t('track.fieldWard')}: {data.ward}</span></div>
              {data.category && <div className="meta-item"><AlertTriangle size={14} /> <span>{t('track.fieldCategory')}: {data.category}</span></div>}
              <div className="meta-item"><Calendar size={14} /> <span>{t('track.fieldDate')}: {data.dateReceived ? new Date(data.dateReceived).toLocaleString('en-IN') : t('common.na')}</span></div>
            </div>

            {statusStages && (
              <div className="track-progress">
                <h3><Activity size={16} /> {t('complaintDetail.statusTimelineTitle')}</h3>
                <StatusTimeline stages={statusStages} />
              </div>
            )}

            {data.department && (
              <div className="track-section">
                <h3><Building2 size={16} /> {t('track.assignedDepartment')}</h3>
                <div className="track-info-card">
                  <div className="track-info-row">
                    <span>{t('track.fieldDepartment')}</span>
                    <strong>{t(getDeptI18nKey(data.department))}</strong>
                  </div>
                </div>
              </div>
            )}

            {data.officer_name && (
              <div className="track-section">
                <h3><User size={16} /> {t('track.assignedOfficer')}</h3>
                <div className="track-info-card">
                  <div className="track-info-row">
                    <span>{t('track.fieldOfficerName')}</span>
                    <strong>{data.officer_name}</strong>
                  </div>
                  {data.officer_role && (
                    <div className="track-info-row">
                      <span>{t('track.fieldOfficerRole')}</span>
                      <strong>{data.officer_role}</strong>
                    </div>
                  )}
                </div>
              </div>
            )}

            {['resolved', 'closed', 'pending_verification'].includes(data.status) && data.resolution_note && (
              <div className="track-section">
                <h3><CheckCircle size={16} /> {t('complaintDetail.resolutionNote')}</h3>
                <div className="track-info-card">
                  <p className="track-resolution-text">{data.resolution_note}</p>
                </div>
              </div>
            )}

            <div className="track-timeline">
              <h3>{t('track.timelineTitle')}</h3>
              {data.timeline?.map((item: any, idx: number) => {
                const Icon = TIMELINE_ICONS[item.label] || CheckCircle;
                const color = TIMELINE_COLORS[item.label] || '#64748b';
                return (
                  <div key={idx} className="timeline-item">
                    <div className="timeline-icon" style={{ background: color }}><Icon size={14} /></div>
                    <div className="timeline-content">
                      <strong>{item.label}</strong>
                      {item.date && <span className="timeline-date">{new Date(item.date).toLocaleString('en-IN')}</span>}
                      {item.detail && <p className="timeline-detail">{item.detail}</p>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TrackComplaint;
