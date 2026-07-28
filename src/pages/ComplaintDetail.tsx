import { useState, useEffect, useCallback } from 'react';
import { useDashboardSocket } from '../hooks/useDashboardSocket';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import HelpWidget from '../components/HelpWidget';
import { getDeptI18nKey } from '../data/departments';
import type { ComplaintDetail } from '../types';
import { ArrowLeft, MapPin, Calendar, Tag, AlertTriangle, CheckCircle, Clock, Link as LinkIcon, ThumbsUp, XCircle, Building2, Phone, User, Activity, Star, Edit3, Save, X, Download } from 'lucide-react';
import { StatusTimeline, useStatusStages } from '../components/StatusTimeline';
import './ComplaintDetail.css';

const STATUS_STYLES: Record<string, string> = {
  open: 'status-open',
  'in-progress': 'status-progress',
  resolved: 'status-resolved',
  pending_verification: 'status-pending-verification',
  closed: 'status-closed',
};

const STATUS_KEY: Record<string, string> = {
  open: 'common.status.open',
  'in-progress': 'common.status.inProgress',
  resolved: 'common.status.resolved',
  pending_verification: 'common.status.pendingVerification',
  closed: 'common.status.closed',
};

const getConfidenceLabel = (confidence: number | null | undefined, t: (key: string) => string): string => {
  if (confidence == null) return t('common.na');
  if (confidence >= 0.8) return t('common.confidence.high');
  if (confidence >= 0.5) return t('common.confidence.medium');
  return t('common.confidence.low');
};

const ComplaintDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { user } = useAuth();
  const [data, setData] = useState<ComplaintDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyResult, setVerifyResult] = useState<{ success: boolean; message: string } | null>(null);
  const [reopenLoading, setReopenLoading] = useState(false);
  const [reopenResult, setReopenResult] = useState<{ success: boolean; message: string } | null>(null);
  const [appealReason, setAppealReason] = useState('');
  const [appealLoading, setAppealLoading] = useState(false);
  const [appealResult, setAppealResult] = useState<{ success: boolean; message: string } | null>(null);
  const [rating, setRating] = useState(0);
  const [ratingLoading, setRatingLoading] = useState(false);
  const [ratingResult, setRatingResult] = useState<{ success: boolean; message: string } | null>(null);
  const [editing, setEditing] = useState(false);
  const [editDescription, setEditDescription] = useState('');
  const [editLocation, setEditLocation] = useState('');
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [nearbyComplaints, setNearbyComplaints] = useState<any[]>([]);
  const [nearbyLoading, setNearbyLoading] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  const fetchDetail = useCallback(async (showLoader = false) => {
    if (!id) return;
    if (showLoader) { setLoading(true); setError(null); }
    try {
      const data = await api.getComplaintDetail(id);
      setData(data);
      if (data.ward && data.predicted_category && data.predicted_category !== 'Uncategorized') {
        setNearbyLoading(true);
        api.getNearbyComplaints(data.ward, data.predicted_category, id).then(setNearbyComplaints).catch(() => {}).finally(() => setNearbyLoading(false));
      }
      if (data.image_path) {
        if (data.image_path.startsWith('http')) {
          setPhotoUrl(data.image_path);
        } else {
          api.getComplaintPhoto(id).then(photoRes => {
            if (photoRes.imageUrl) setPhotoUrl(photoRes.imageUrl);
          }).catch(() => {});
        }
      }
    } catch (err: any) {
      if (showLoader) setError(err.message);
    } finally {
      if (showLoader) setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    let mounted = true;
    if (!id) { setLoading(false); return; }
    const fetchWithMount = async (showLoader: boolean) => {
      if (!mounted) return;
      await fetchDetail(showLoader);
    };
    fetchWithMount(true);
    const interval = setInterval(() => fetchWithMount(false), 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, [id, fetchDetail]);

  useDashboardSocket({
    onEvent: () => { fetchDetail(false); },
  });

  const handleVerify = async () => {
    if (!data?.incident?.id) return;
    setVerifyLoading(true);
    setVerifyResult(null);
    try {
      const res = await api.verifyResolution(data.incident.id, verifyCode);
      setVerifyResult({ success: true, message: t('complaintDetail.verifySuccess') });
      setVerifyCode('');
      // Refresh data to show resolved status
      const refreshed = await api.getComplaintDetail(id!);
      setData(refreshed);
    } catch (err: any) {
      setVerifyResult({ success: false, message: err.message || t('complaintDetail.verifyError') });
    } finally {
      setVerifyLoading(false);
    }
  };

  const handleRate = async () => {
    if (!data?.id || rating < 1) return;
    setRatingLoading(true);
    setRatingResult(null);
    try {
      await api.rateComplaint(data.id, rating);
      setRatingResult({ success: true, message: t('complaintDetail.ratingSuccess') });
      const refreshed = await api.getComplaintDetail(id!);
      setData(refreshed);
    } catch (err: any) {
      setRatingResult({ success: false, message: err.message || t('complaintDetail.ratingError') });
    } finally {
      setRatingLoading(false);
    }
  };

  const handleReopen = async () => {
    if (!data?.incident?.id) return;
    setReopenLoading(true);
    setReopenResult(null);
    try {
      const res = await api.reopenIncident(data.incident.id);
      setReopenResult({ success: true, message: t('complaintDetail.reopenSuccess') });
      const refreshed = await api.getComplaintDetail(id!);
      setData(refreshed);
    } catch (err: any) {
      setReopenResult({ success: false, message: err.message || t('complaintDetail.reopenError') });
    } finally {
      setReopenLoading(false);
    }
  };

  const handleAppeal = async () => {
    if (!data?.incident?.id) return;
    setAppealLoading(true);
    setAppealResult(null);
    try {
      const res = await api.appealIncident(data.incident.id, appealReason);
      setAppealResult({ success: true, message: t('complaintDetail.appealSuccess') });
      setAppealReason('');
      const refreshed = await api.getComplaintDetail(id!);
      setData(refreshed);
    } catch (err: any) {
      setAppealResult({ success: false, message: err.message || t('complaintDetail.appealError') });
    } finally {
      setAppealLoading(false);
    }
  };

  const handleEdit = async () => {
    if (!data) return;
    setEditLoading(true);
    setEditError(null);
    try {
      const updated = await api.updateComplaint(data.id, {
        description: editDescription !== data.description ? editDescription : undefined,
        location: editLocation !== data.location ? editLocation : undefined,
      });
      setData(prev => prev ? { ...prev, description: updated.description, location: updated.location } : prev);
      setEditing(false);
    } catch (err: any) {
      setEditError(err.message || 'Failed to update');
    } finally {
      setEditLoading(false);
    }
  };

  const startEditing = () => {
    if (!data) return;
    setEditDescription(data.description || '');
    setEditLocation(data.location || '');
    setEditError(null);
    setEditing(true);
  };

  const incidentStatus = data?.incident?.status || 'open';
  const confidenceLabel = data?.confidence != null ? `${getConfidenceLabel(data.confidence, t)} ${t('common.confidence.label')}` : '';
  const statusStages = useStatusStages(
    data?.date_received ?? null,
    incidentStatus,
    !!(data?.assigned_officer?.name || data?.assigned_officer?.phone),
    !!data?.predicted_category,
  );
  const canEdit = user?.role === 'Citizen' && data?.date_received && (Date.now() - new Date(data.date_received).getTime()) < 15 * 60 * 1000;

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>{t('complaintDetail.loading')}</span></div>;
  if (error) return <div className="page-error">{t('common.error')}: {error}</div>;
  if (!data) return <div className="page-error">{t('complaintDetail.notFound')}</div>;

  const timeline = [
    { label: t('complaintDetail.timelineSubmitted'), date: data.date_received, icon: CheckCircle, color: '#3b82f6' },
    { label: t('complaintDetail.timelineCategorized'), date: data.date_received, icon: ThumbsUp, color: '#8b5cf6', detail: `${data.predicted_category} — ${confidenceLabel}` },
    { label: t('complaintDetail.timelineSimilarity'), date: data.date_received, icon: data.incident ? LinkIcon : XCircle, color: data.incident ? '#16a34a' : '#64748b', detail: data.incident ? t('common.groupedWithSimilar') : t('complaintDetail.timelineNoSimilar') },
    { label: t('complaintDetail.timelineCurrentStatus'), date: null, icon: Clock, color: '#eab308', detail: t(STATUS_KEY[incidentStatus] || 'common.status.open').toUpperCase() },
  ];

  const priorityEntries = data.incident?.priority_history?.map((h: any) => ({
    label: t('complaintDetail.timelinePriorityUpdated'),
    date: h.changed_at,
    icon: AlertTriangle,
    color: '#ea580c',
    detail: `${h.reason || t('complaintDetail.timelinePriorityUpdated')}`
  })) || [];
  const fullTimeline = [...timeline, ...priorityEntries];

  return (
    <div className="complaint-detail-page">
      <Header title={t('complaintDetail.headerTitle')} subtitle={`${t('complaintDetail.headerSubtitle')} ${data.id}`} />
      <div className="page-content">
        <button className="back-btn" onClick={() => navigate('/my-complaints')}><ArrowLeft size={18} /> {t('complaintDetail.backButton')}</button>

        <div className="detail-grid">
          <div className="main-card glass-card">
            <div className="status-header">
              <h2>{data.title || t('common.untitled')}</h2>
              <div className="status-actions">
                <span className={`status-badge ${STATUS_STYLES[incidentStatus] || 'status-open'}`}>{t(STATUS_KEY[incidentStatus] || 'common.status.open')}</span>
                {canEdit && !editing && (
                  <button className="edit-complaint-btn" onClick={startEditing} title="Edit complaint">
                    <Edit3 size={14} /> Edit
                  </button>
                )}
              </div>
            </div>
            {editing ? (
              <div className="edit-fields">
                <label className="edit-label">Description</label>
                <textarea
                  className="edit-textarea"
                  value={editDescription}
                  onChange={e => setEditDescription(e.target.value)}
                  rows={4}
                  disabled={editLoading}
                />
                <label className="edit-label">Location</label>
                <input
                  className="edit-input"
                  value={editLocation}
                  onChange={e => setEditLocation(e.target.value)}
                  disabled={editLoading}
                />
                <div className="edit-actions">
                  <button className="cancel-edit-btn" onClick={() => setEditing(false)} disabled={editLoading}>
                    <X size={14} /> Cancel
                  </button>
                  <button className="save-edit-btn" onClick={handleEdit} disabled={editLoading || !editDescription.trim()}>
                    <Save size={14} /> {editLoading ? 'Saving...' : 'Save'}
                  </button>
                </div>
                {editError && <p className="edit-error">{editError}</p>}
              </div>
            ) : (
              <p className="detail-description">{data.description}</p>
            )}

            {photoUrl && (
              <div className="detail-photo" onClick={() => setLightboxOpen(true)}>
                <img src={photoUrl} alt={t('complaintDetail.imageAlt')} className="photo-img" />
              </div>
            )}
            {lightboxOpen && photoUrl && (
              <div className="lightbox-overlay" onClick={() => setLightboxOpen(false)}>
                <div className="lightbox-content" onClick={e => e.stopPropagation()}>
                  <button className="lightbox-close-btn" onClick={() => setLightboxOpen(false)}><X size={20} /></button>
                  <a className="lightbox-download-btn" href={photoUrl} download target="_blank" rel="noopener noreferrer"><Download size={16} /> Download</a>
                  <img src={photoUrl} alt={t('complaintDetail.imageAlt')} className="lightbox-image" />
                </div>
              </div>
            )}

            <div className="detail-meta-grid">
              <div className="meta-item"><MapPin size={16} /> <span>{editing ? editLocation || '(not set)' : (data.location || t('common.na'))}</span></div>
              <div className="meta-item"><Tag size={16} /> <span>{data.ward || t('common.na')}</span></div>
              <div className="meta-item"><Calendar size={16} /> <span>{data.date_received ? new Date(data.date_received).toLocaleString('en-IN') : t('common.na')}</span></div>
              <div className="meta-item"><AlertTriangle size={16} /> <span>{data.predicted_category || t('common.uncategorized')}</span></div>
              {data.department && <div className="meta-item"><Building2 size={16} /> <span>{t(getDeptI18nKey(data.department))}</span></div>}
            </div>

            {nearbyComplaints.length > 0 && (
              <div className="nearby-section">
                <h3><MapPin size={16} /> {t('complaintDetail.nearbyTitle')}</h3>
                <div className="nearby-list">
                  {nearbyComplaints.slice(0, 5).map((nc: any) => (
                    <div key={nc.complaint_id} className="nearby-item">
                      <div className="nearby-item-main">
                        <span className="nearby-status">{nc.status}</span>
                        <span className="nearby-priority">{nc.priority || '—'}</span>
                      </div>
                      <div className="nearby-item-meta">
                        <span>{nc.days_open > 0 ? `${nc.days_open}d open` : 'Just reported'}</span>
                        <span>{nc.ward}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {nearbyLoading && <div className="nearby-loading">{t('common.loading')}</div>}

            <div className="ai-section">
              <h3><ThumbsUp size={18} /> {t('complaintDetail.sectionCategory')}</h3>
              <div className="ai-metrics">
                <div className="ai-metric">
                  <span className="label">{t('common.matchConfidence')}</span>
                  <div className="metric-bar"><div className="metric-fill" style={{ width: `${Math.round((data.confidence || 0) * 100)}%` }}></div></div>
                  <span className="value">{getConfidenceLabel(data.confidence, t)}</span>
                </div>
              </div>
              {data.merge_reason && data.incident && (
                <div className="merge-banner">
                  <span className="merge-banner-icon">📋</span>
                  <div className="merge-banner-text">
                    <strong>Your complaint has been grouped with {(data.incident.cluster_size ?? 1) - 1} other report{((data.incident.cluster_size ?? 1) - 1) !== 1 ? 's' : ''} of the same issue.</strong>
                    <span className="merge-banner-status">Current status: <strong>{t(STATUS_KEY[data.incident.status || 'open'] || 'common.status.open')}</strong></span>
                  </div>
                </div>
              )}
            </div>

            {data.photo_duplicate_flag && (
              <div className="incident-section">
                <h3><AlertTriangle size={18} /> {t('complaintDetail.photoDuplicate.title')}</h3>
                <div className="incident-card" style={{
                  borderLeft: data.photo_duplicate_flag === 'reused_image'
                    ? '3px solid #ef4444'
                    : '3px solid #f59e0b'
                }}>
                  <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                    {t(`complaintDetail.photoDuplicate.${data.photo_duplicate_flag}`)}
                  </p>
                </div>
              </div>
            )}

            {data.incident && (
              <div className="incident-section">
                <h3><LinkIcon size={18} /> {t('complaintDetail.sectionIncident')}</h3>
                <div className="incident-card">
                  <div className="incident-row"><span>{t('complaintDetail.fieldIncidentId')}</span><strong>{data.incident.incident_number}</strong></div>
                  <div className="incident-row"><span>{t('complaintDetail.fieldCategory')}</span><strong>{data.incident.category}</strong></div>
                  <div className="incident-row"><span>{t('complaintDetail.fieldDepartment')}</span><strong>{t(getDeptI18nKey(data.department || data.incident.category || ''))}</strong></div>
                  <div className="incident-row"><span>{t('complaintDetail.fieldStatus')}</span><strong>{t(STATUS_KEY[data.incident.status || 'open'] || 'common.status.open')}</strong></div>
                  <div className="incident-row"><span>{t('complaintDetail.fieldPriority')}</span><strong>{data.incident.priority_label}</strong></div>
                  <div className="incident-row"><span>{t('complaintDetail.fieldClusterSize')}</span><strong>{data.incident.cluster_size}</strong></div>
                  {data.incident.recommended_action && <div className="incident-row"><span>{t('complaintDetail.fieldAction')}</span><span>{data.incident.recommended_action}</span></div>}
                  {['resolved', 'closed'].includes(data.incident.status || '') && data.incident.resolution_note && (
                    <div className="resolution-note-section">
                      <span className="resolution-note-label">{t('complaintDetail.resolutionNote')}</span>
                      <p className="resolution-note-text">{data.incident.resolution_note}</p>
                    </div>
                  )}
                </div>

                {user?.role === 'Citizen' && data.incident.status === 'pending_verification' && (
                  <div className="verify-section">
                    <h4><CheckCircle size={16} /> {t('complaintDetail.verifyTitle')}</h4>
                    <p className="verify-prompt">{t('complaintDetail.verifyPrompt')}</p>
                    <div className="verify-input-group">
                      <input
                        type="text"
                        maxLength={6}
                        placeholder={t('complaintDetail.verifyPlaceholder')}
                        value={verifyCode}
                        onChange={e => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                        className="verify-input"
                        disabled={verifyLoading}
                      />
                      <button
                        className="verify-btn"
                        onClick={handleVerify}
                        disabled={verifyLoading || verifyCode.length !== 6}
                      >
                        {verifyLoading ? <div className="spinner-sm" /> : t('complaintDetail.verifySubmit')}
                      </button>
                    </div>
                    {verifyResult && (
                      <p className={`verify-result ${verifyResult.success ? 'verify-success' : 'verify-error'}`}>
                        {verifyResult.message}
                      </p>
                    )}
                  </div>
                )}

                {user?.role === 'Citizen' && ['resolved', 'closed'].includes(data.incident?.status || '') && data.citizen_rating == null && (
                  <div className="rating-section">
                    <h4><Star size={16} /> {t('complaintDetail.rateTitle')}</h4>
                    <p className="rating-prompt">{t('complaintDetail.ratePrompt')}</p>
                    <div className="stars">
                      {[1, 2, 3, 4, 5].map(s => (
                        <Star
                          key={s}
                          size={28}
                          className={`star ${s <= rating ? 'filled' : ''}`}
                          onClick={() => !ratingLoading && setRating(s)}
                        />
                      ))}
                    </div>
                    <button
                      className="rate-btn"
                      onClick={handleRate}
                      disabled={ratingLoading || rating < 1}
                    >
                      {ratingLoading ? <div className="spinner-sm" /> : t('complaintDetail.rateSubmit')}
                    </button>
                    {ratingResult && (
                      <p className={`rate-result ${ratingResult.success ? 'rate-success' : 'rate-error'}`}>
                        {ratingResult.message}
                      </p>
                    )}
                  </div>
                )}

                {user?.role === 'Citizen' && ['resolved', 'pending_verification', 'closed'].includes(data.incident?.status || '') && (
                  <div className="reopen-section">
                    <p className="reopen-prompt">{t('complaintDetail.reopenPrompt')}</p>
                    <button
                      className="reopen-btn"
                      onClick={handleReopen}
                      disabled={reopenLoading}
                    >
                      {reopenLoading ? <div className="spinner-sm" /> : t('complaintDetail.reopenButton')}
                    </button>
                    {reopenResult && (
                      <p className={`reopen-result ${reopenResult.success ? 'reopen-success' : 'reopen-error'}`}>
                        {reopenResult.message}
                      </p>
                    )}
                  </div>
                )}

                {user?.role === 'Citizen' && ['resolved', 'closed', 'pending_verification'].includes(data.incident?.status || '') && (
                  <div className="appeal-section">
                    <h4><AlertTriangle size={16} /> {t('complaintDetail.appealTitle')}</h4>
                    <p className="appeal-prompt">{t('complaintDetail.appealPrompt')}</p>
                    <textarea
                      className="appeal-input"
                      placeholder={t('complaintDetail.appealPlaceholder')}
                      value={appealReason}
                      onChange={e => setAppealReason(e.target.value)}
                      rows={3}
                      disabled={appealLoading}
                    />
                    <button
                      className="appeal-btn"
                      onClick={handleAppeal}
                      disabled={appealLoading || appealReason.trim().length < 10}
                    >
                      {appealLoading ? <div className="spinner-sm" /> : t('complaintDetail.appealSubmit')}
                    </button>
                    {appealResult && (
                      <p className={`appeal-result ${appealResult.success ? 'appeal-success' : 'appeal-error'}`}>
                        {appealResult.message}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {data.predicted_category === 'General / Manual Triage' ? (
              <div className="incident-section">
                <h3><User size={18} /> {t('complaintDetail.sectionOfficer')}</h3>
                <div className="incident-card" style={{ borderLeft: '3px solid #f59e0b' }}>
                  <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                    <strong style={{ color: 'var(--text-primary)' }}>{t('complaintDetail.noOfficerYet')}</strong><br />
                    {t('complaintDetail.underReview')}
                  </p>
                </div>
              </div>
            ) : data.assigned_officer && data.assigned_officer.name ? (
              <div className="incident-section">
                <h3><User size={18} /> {t('complaintDetail.sectionOfficer')}</h3>
                <div className="incident-card">
                  <div className="incident-row">
                    <span>{t('complaintDetail.fieldOfficerName')}</span>
                    <strong>{data.assigned_officer.name}</strong>
                  </div>
                  <div className="incident-row">
                    <span>{t('complaintDetail.fieldOfficerRole')}</span>
                    <strong>{data.assigned_officer.role}</strong>
                  </div>
                  <div className="incident-row">
                    <span>{t('complaintDetail.fieldOfficerPhone')}</span>
                    <strong>
                      {data.assigned_officer.phone ? (
                        <a href={`tel:${data.assigned_officer.phone}`} style={{ color: 'inherit', textDecoration: 'none' }}>
                          <Phone size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                          {data.assigned_officer.phone}
                        </a>
                      ) : t('common.na')}
                    </strong>
                  </div>
                  <div className="incident-row">
                    <span>{t('complaintDetail.fieldOfficerZone')}</span>
                    <strong>{data.assigned_officer.zone_name || t('common.na')}</strong>
                  </div>
                  <div className="incident-row">
                    <span>{t('complaintDetail.fieldOfficerCorporation')}</span>
                    <strong>{data.assigned_officer.corporation_id || t('common.na')}</strong>
                  </div>
                  {data.assigned_officer.fallback_reason && (
                    <p style={{ margin: '8px 0 0', fontSize: 12, color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: 8 }}>{data.assigned_officer.fallback_reason}</p>
                  )}
                </div>
              </div>
            ) : data.assigned_officer?.error ? (
              <div className="incident-section">
                <h3><User size={18} /> {t('complaintDetail.sectionOfficer')}</h3>
                <div className="incident-card" style={{ borderLeft: '3px solid #f59e0b' }}>
                  <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>
                    {t('complaintDetail.officerNotFound')}
                  </p>
                </div>
              </div>
            ) : null}
          </div>

          <div className="side-card glass-card">
            <h3><Activity size={16} /> {t('complaintDetail.statusTimelineTitle')}</h3>
            <StatusTimeline stages={statusStages} />

            <h3 style={{ marginTop: 20 }}>{t('complaintDetail.sectionTimeline')}</h3>
            <div className="timeline">
              {fullTimeline.map((item, idx) => (
                <div key={idx} className="timeline-item">
                  <div className="timeline-icon" style={{ background: item.color }}><item.icon size={16} /></div>
                  <div className="timeline-content">
                    <strong>{item.label}</strong>
                    {item.date && <span className="timeline-date">{new Date(item.date).toLocaleString('en-IN')}</span>}
                    {item.detail && <p className="timeline-detail">{item.detail}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <HelpWidget />
    </div>
  );
};

export default ComplaintDetailPage;
