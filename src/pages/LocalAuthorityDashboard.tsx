import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import { MapPin, Tag, AlertTriangle, Clock, FileText, ArrowUpRight, CheckCircle, Loader2, ShieldAlert } from 'lucide-react';
import './LocalAuthorityDashboard.css';

interface WardComplaint {
  id: string;
  title: string;
  description: string;
  location: string;
  ward: string;
  predicted_category: string;
  priority: string;
  date_received: string;
  incident?: {
    id: string;
    incident_number: string;
    status: string;
    escalated: boolean;
    days_open: number;
  } | null;
}

const STATUS_STYLES: Record<string, string> = {
  open: 'status-open',
  'in-progress': 'status-progress',
  resolved: 'status-resolved',
};

const STATUS_KEY: Record<string, string> = {
  open: 'common.status.open',
  'in-progress': 'common.status.inProgress',
  resolved: 'common.status.resolved',
};

const LocalAuthorityDashboard = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isCommissioner = user?.role === 'Commissioner';
  const isCouncillor = user?.role === 'Councillor';

  const [ward, setWard] = useState<string>(() => {
    if (isCouncillor && user?.ward) return user.ward;
    return 'Ward 1';
  });
  const [complaints, setComplaints] = useState<WardComplaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.getWardComplaints(ward)
      .then(res => {
        if (!cancelled) setComplaints(res.complaints || []);
      })
      .catch(err => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ward]);

  const handleEscalate = async (incidentId: string) => {
    if (!incidentId) return;
    setActionLoading(incidentId);
    try {
      await api.escalateIncident(incidentId, 'Escalated by ward authority');
      setComplaints(prev => prev.map(c =>
        c.incident?.id === incidentId
          ? { ...c, incident: { ...c.incident, escalated: true } }
          : c
      ));
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleResolve = async (incidentId: string) => {
    if (!incidentId) return;
    setActionLoading(incidentId);
    try {
      await api.updateIncidentStatus(incidentId, 'resolved');
      setComplaints(prev => prev.map(c =>
        c.incident?.id === incidentId
          ? { ...c, incident: { ...c.incident, status: 'resolved' } }
          : c
      ));
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const unresolved = complaints.filter(c => !c.incident || c.incident.status !== 'resolved');
  const escalated = complaints.filter(c => c.incident?.escalated);

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>{t('common.na')}</span></div>;
  if (error) return <div className="page-error">{t('common.error')}: {error}</div>;

  return (
    <div className="la-dashboard">
      <Header
        title={isCommissioner ? t('nav.commissionerDashboard') : t('nav.councillorDashboard')}
        subtitle={`${t('common.status.open')} — ${t('complaintDetail.fieldStatus')}: ${ward}`}
      />
      <div className="page-content">
        <div className="la-toolbar">
          <div className="ward-selector">
            <MapPin size={16} />
            <input
              type="text"
              value={ward}
              onChange={e => setWard(e.target.value)}
              className="ward-input"
              disabled={isCouncillor}
              placeholder="Ward name"
            />
          </div>
          <div className="la-stats">
            <div className="stat-chip"><FileText size={14} /> {unresolved.length} open</div>
            <div className="stat-chip escalated"><ShieldAlert size={14} /> {escalated.length} escalated</div>
          </div>
        </div>

        {unresolved.length === 0 ? (
          <div className="empty-state"><FileText size={48} /><p>No open complaints in this ward</p></div>
        ) : (
          <div className="complaint-list">
            {unresolved.map(c => {
              const days = c.incident?.days_open || 0;
              return (
                <div key={c.id} className={`complaint-row ${c.incident?.escalated ? 'is-escalated' : ''}`}>
                  <div className="cr-header">
                    <span className="cr-title">{c.title}</span>
                    <span className={`cr-status ${STATUS_STYLES[c.incident?.status || 'open']}`}>
                      {t(STATUS_KEY[c.incident?.status || 'open'] || 'common.status.open')}
                    </span>
                  </div>
                  <p className="cr-desc">{c.description}</p>
                  <div className="cr-meta">
                    <span><Tag size={12} /> {c.predicted_category}</span>
                    <span><MapPin size={12} /> {c.location}</span>
                    {c.incident && <span><Clock size={12} /> {days}d</span>}
                    {c.incident?.escalated && <span className="escalated-badge"><ShieldAlert size={12} /> Escalated</span>}
                  </div>
                  <div className="cr-actions">
                    {c.incident && !c.incident.escalated && (
                      <button
                        className="action-btn escalate-btn"
                        onClick={() => handleEscalate(c.incident!.id)}
                        disabled={actionLoading === c.incident.id}
                      >
                        {actionLoading === c.incident.id ? <Loader2 size={14} className="spin" /> : <ArrowUpRight size={14} />}
                        {t('la.flagEscalation')}
                      </button>
                    )}
                    {isCommissioner && c.incident && c.incident.status !== 'resolved' && (
                      <button
                        className="action-btn resolve-btn"
                        onClick={() => handleResolve(c.incident!.id)}
                        disabled={actionLoading === c.incident.id}
                      >
                        {actionLoading === c.incident.id ? <Loader2 size={14} className="spin" /> : <CheckCircle size={14} />}
                        {t('la.markResolved')}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default LocalAuthorityDashboard;
