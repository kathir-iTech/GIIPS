import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import { getDeptI18nKey } from '../data/departments';
import type { ComplaintDetail } from '../types';
import { ArrowLeft, MapPin, Calendar, Tag, AlertTriangle, CheckCircle, Clock, Link as LinkIcon, ThumbsUp, XCircle, Building2, Phone, User } from 'lucide-react';
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

  useEffect(() => {
    let cancelled = false;
    if (!id) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    api.getComplaintDetail(id)
      .then(data => {
        if (!cancelled) {
          setData(data);
          if (data.image_path) {
            if (data.image_path.startsWith('http')) {
              setPhotoUrl(data.image_path);
            } else {
              api.getComplaintPhoto(id).then(photoRes => {
                if (!cancelled && photoRes.imageUrl) setPhotoUrl(photoRes.imageUrl);
              }).catch(() => {});
            }
          }
        }
      })
      .catch(err => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [id]);

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

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>{t('complaintDetail.loading')}</span></div>;
  if (error) return <div className="page-error">{t('common.error')}: {error}</div>;
  if (!data) return <div className="page-error">{t('complaintDetail.notFound')}</div>;

  const incidentStatus = data.incident?.status || 'open';
  const confidenceLabel = data.confidence != null ? `${getConfidenceLabel(data.confidence, t)} ${t('common.confidence.label')}` : '';

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

  const friendlyMergeReason = (reason: string): string => {
    if (!reason) return '';
    if (reason.includes('Automated merge') || reason.includes('merged')) {
      return t('complaintDetail.mergeGrouped');
    }
    return t('complaintDetail.mergeNewCase');
  };

  return (
    <div className="complaint-detail-page">
      <Header title={t('complaintDetail.headerTitle')} subtitle={`${t('complaintDetail.headerSubtitle')} ${data.id}`} />
      <div className="page-content">
        <button className="back-btn" onClick={() => navigate('/my-complaints')}><ArrowLeft size={18} /> {t('complaintDetail.backButton')}</button>

        <div className="detail-grid">
          <div className="main-card glass-card">
            <div className="status-header">
              <h2>{data.title || t('common.untitled')}</h2>
              <span className={`status-badge ${STATUS_STYLES[incidentStatus] || 'status-open'}`}>{t(STATUS_KEY[incidentStatus] || 'common.status.open')}</span>
            </div>
            <p className="detail-description">{data.description}</p>

            {photoUrl && (
              <div className="detail-photo">
                <img src={photoUrl} alt={t('complaintDetail.imageAlt')} className="photo-img" />
              </div>
            )}

            <div className="detail-meta-grid">
              <div className="meta-item"><MapPin size={16} /> <span>{data.location || t('common.na')}</span></div>
              <div className="meta-item"><Tag size={16} /> <span>{data.ward || t('common.na')}</span></div>
              <div className="meta-item"><Calendar size={16} /> <span>{data.date_received ? new Date(data.date_received).toLocaleString('en-IN') : t('common.na')}</span></div>
              <div className="meta-item"><AlertTriangle size={16} /> <span>{data.predicted_category || t('common.uncategorized')}</span></div>
              {data.department && <div className="meta-item"><Building2 size={16} /> <span>{t(getDeptI18nKey(data.department))}</span></div>}
            </div>

            <div className="ai-section">
              <h3><ThumbsUp size={18} /> {t('complaintDetail.sectionCategory')}</h3>
              <div className="ai-metrics">
                <div className="ai-metric">
                  <span className="label">{t('common.matchConfidence')}</span>
                  <div className="metric-bar"><div className="metric-fill" style={{ width: `${Math.round((data.confidence || 0) * 100)}%` }}></div></div>
                  <span className="value">{getConfidenceLabel(data.confidence, t)}</span>
                </div>
                <div className="ai-metric">
                  <span className="label">{t('common.mergedWith')}</span>
                  <span className={`value ${data.incident ? 'duplicate-yes' : 'duplicate-no'}`}>{data.incident ? t('common.yes') : t('common.no')}</span>
                </div>
              </div>
              {data.merge_reason && <p className="merge-reason">{friendlyMergeReason(data.merge_reason)}</p>}
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
            <h3>{t('complaintDetail.sectionTimeline')}</h3>
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
    </div>
  );
};

export default ComplaintDetailPage;
