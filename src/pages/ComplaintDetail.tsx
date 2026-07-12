import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import Header from '../components/Header';
import type { ComplaintDetail } from '../types';
import { ArrowLeft, MapPin, Calendar, Tag, AlertTriangle, CheckCircle, Clock, Link as LinkIcon, ThumbsUp, XCircle, Building2 } from 'lucide-react';
import './ComplaintDetail.css';

const STATUS_STYLES: Record<string, string> = {
  open: 'status-open',
  'in-progress': 'status-progress',
  resolved: 'status-resolved',
  closed: 'status-closed',
};

const ComplaintDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<ComplaintDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);

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

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>Loading complaint details...</span></div>;
  if (error) return <div className="page-error">Error: {error}</div>;
  if (!data) return <div className="page-error">Complaint not found.</div>;

  const incidentStatus = data.incident?.status || 'open';

  const timeline = [
    { label: 'Submitted', date: data.date_received, icon: CheckCircle, color: '#3b82f6' },
    { label: 'Categorized', date: data.date_received, icon: ThumbsUp, color: '#8b5cf6', detail: `${data.predicted_category} — ${data.confidence != null ? (data.confidence >= 0.8 ? 'High' : data.confidence >= 0.5 ? 'Medium' : 'Low') : ''} confidence` },
    { label: 'Similarity Check', date: data.date_received, icon: data.incident ? LinkIcon : XCircle, color: data.incident ? '#16a34a' : '#64748b', detail: data.incident ? 'Grouped with similar complaints' : 'No similar complaints found' },
    { label: 'Current Status', date: null, icon: Clock, color: '#eab308', detail: incidentStatus.replace('-', ' ').toUpperCase() },
  ];

  const priorityEntries = data.incident?.priority_history?.map((h: any) => ({
    label: 'Priority Updated',
    date: h.changed_at,
    icon: AlertTriangle,
    color: '#ea580c',
    detail: `${h.reason || 'Priority adjusted'}`
  })) || [];
  const fullTimeline = [...timeline, ...priorityEntries];

  const friendlyMergeReason = (reason: string): string => {
    if (!reason) return '';
    if (reason.includes('Automated merge') || reason.includes('merged')) {
      return 'Your complaint was grouped with one or more similar reports to help prioritize a faster response.';
    }
    return 'A new case was opened for your complaint.';
  };

  return (
    <div className="complaint-detail-page">
      <Header title="Complaint Details" subtitle={`Reference: ${data.id}`} />
      <div className="page-content">
        <button className="back-btn" onClick={() => navigate('/my-complaints')}><ArrowLeft size={18} /> Back to My Complaints</button>

        <div className="detail-grid">
          <div className="main-card glass-card">
            <div className="status-header">
              <h2>{data.title || 'Untitled Complaint'}</h2>
              <span className={`status-badge ${STATUS_STYLES[incidentStatus] || 'status-open'}`}>{incidentStatus.replace('-', ' ')}</span>
            </div>
            <p className="detail-description">{data.description}</p>

            {photoUrl && (
              <div className="detail-photo">
                <img src={photoUrl} alt="Complaint evidence" className="photo-img" />
              </div>
            )}

            <div className="detail-meta-grid">
              <div className="meta-item"><MapPin size={16} /> <span>{data.location || 'N/A'}</span></div>
              <div className="meta-item"><Tag size={16} /> <span>{data.ward || 'N/A'}</span></div>
              <div className="meta-item"><Calendar size={16} /> <span>{data.date_received ? new Date(data.date_received).toLocaleString('en-IN') : 'N/A'}</span></div>
              <div className="meta-item"><AlertTriangle size={16} /> <span>{data.predicted_category || 'Uncategorized'}</span></div>
              {data.department && <div className="meta-item"><Building2 size={16} /> <span>{data.department}</span></div>}
            </div>

            <div className="ai-section">
              <h3><ThumbsUp size={18} /> Category & Priority</h3>
              <div className="ai-metrics">
                <div className="ai-metric">
                  <span className="label">Match confidence</span>
                  <div className="metric-bar"><div className="metric-fill" style={{ width: `${Math.round((data.confidence || 0) * 100)}%` }}></div></div>
                  <span className="value">{data.confidence != null ? (data.confidence >= 0.8 ? 'High' : data.confidence >= 0.5 ? 'Medium' : 'Low') : 'N/A'}</span>
                </div>
                <div className="ai-metric">
                  <span className="label">Merged with similar complaints</span>
                  <span className={`value ${data.incident ? 'duplicate-yes' : 'duplicate-no'}`}>{data.incident ? 'Yes' : 'No'}</span>
                </div>
              </div>
              {data.merge_reason && <p className="merge-reason">{friendlyMergeReason(data.merge_reason)}</p>}
            </div>

            {data.incident && (
              <div className="incident-section">
                <h3><LinkIcon size={18} /> Linked Incident</h3>
                <div className="incident-card">
                  <div className="incident-row"><span>Incident ID:</span><strong>{data.incident.incident_number}</strong></div>
                  <div className="incident-row"><span>Category:</span><strong>{data.incident.category}</strong></div>
                  <div className="incident-row"><span>Department:</span><strong>{data.department || data.incident.category || 'N/A'}</strong></div>
                  <div className="incident-row"><span>Status:</span><strong>{data.incident.status?.replace('-', ' ')}</strong></div>
                  <div className="incident-row"><span>Priority:</span><strong>{data.incident.priority_label}</strong></div>
                  <div className="incident-row"><span>Similar complaints grouped:</span><strong>{data.incident.cluster_size}</strong></div>
                  {data.incident.recommended_action && <div className="incident-row"><span>Action:</span><span>{data.incident.recommended_action}</span></div>}
                </div>
              </div>
            )}
          </div>

          <div className="side-card glass-card">
            <h3>Complaint Timeline</h3>
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

export default ComplaintDetail;
