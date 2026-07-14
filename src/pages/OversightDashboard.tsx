import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import { MapPin, Tag, Clock, ShieldAlert, FileText, AlertTriangle, Loader2 } from 'lucide-react';
import './OversightDashboard.css';

interface EscalatedIncident {
  id: string;
  incident_number: string;
  category: string;
  ward: string;
  status: string;
  priority_label: string;
  priority_score: number;
  summary: string;
  days_open: number;
  escalated_at: string;
  escalated_by: string;
  escalation_reason: string;
  complaints: { id: string; text: string }[];
}

const STATUS_KEY: Record<string, string> = {
  open: 'common.status.open',
  'in-progress': 'common.status.inProgress',
  resolved: 'common.status.resolved',
};

const OversightDashboard = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isCollector = user?.role === 'Collector';
  const roleLabel = isCollector ? 'Collector' : 'MLA';

  const [incidents, setIncidents] = useState<EscalatedIncident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<EscalatedIncident | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.getEscalatedIncidents()
      .then(res => {
        if (!cancelled) setIncidents(res.incidents || []);
      })
      .catch(err => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>{t('common.na')}</span></div>;
  if (error) return <div className="page-error">{t('common.error')}: {error}</div>;

  return (
    <div className="oversight-dashboard">
      <Header
        title={roleLabel}
        subtitle={t('nav.oversight')}
      />
      <div className="page-content">
        <div className="os-header">
          <div className="os-title-group">
            <ShieldAlert size={20} className="os-icon" />
            <div>
              <h2>{t('os.escalatedIncidents')}</h2>
              <span className="os-subtitle">{incidents.length} {t('incidents.resultsCount', { count: incidents.length })}</span>
            </div>
          </div>
        </div>

        {incidents.length === 0 ? (
          <div className="empty-state">
            <AlertTriangle size={48} />
            <h3>{t('os.noEscalated')}</h3>
            <p>{t('os.noEscalatedDesc')}</p>
          </div>
        ) : (
          <div className="os-split">
            <div className="os-list">
              {incidents.map(inc => (
                <div
                  key={inc.id}
                  className={`os-card ${selectedIncident?.id === inc.id ? 'selected' : ''}`}
                  onClick={() => setSelectedIncident(inc)}
                >
                  <div className="os-card-header">
                    <strong>{inc.incident_number}</strong>
                    <span className="os-priority" data-level={inc.priority_label?.toLowerCase()}>{inc.priority_label}</span>
                  </div>
                  <p className="os-card-summary">{inc.summary || inc.category}</p>
                  <div className="os-card-meta">
                    <span><MapPin size={12} /> {inc.ward}</span>
                    <span><Tag size={12} /> {inc.category}</span>
                    <span><Clock size={12} /> {inc.days_open}d</span>
                    <span className="os-escalated-by"><ShieldAlert size={12} /> {inc.escalated_by}</span>
                  </div>
                  <div className="os-card-reason">{inc.escalation_reason}</div>
                </div>
              ))}
            </div>

            <div className="os-detail">
              {selectedIncident ? (
                <div className="os-detail-card">
                  <h3>{selectedIncident.incident_number}</h3>
                  <div className="os-detail-meta">
                    <div className="os-detail-row"><span>Category</span><strong>{selectedIncident.category}</strong></div>
                    <div className="os-detail-row"><span>Ward</span><strong>{selectedIncident.ward}</strong></div>
                    <div className="os-detail-row"><span>Status</span><strong>{t(STATUS_KEY[selectedIncident.status] || 'common.status.open')}</strong></div>
                    <div className="os-detail-row"><span>Priority</span><strong>{selectedIncident.priority_label} ({selectedIncident.priority_score})</strong></div>
                    <div className="os-detail-row"><span>Days Open</span><strong>{selectedIncident.days_open}d</strong></div>
                    <div className="os-detail-row"><span>Escalated by</span><strong>{selectedIncident.escalated_by}</strong></div>
                    <div className="os-detail-row"><span>Escalated at</span><strong>{selectedIncident.escalated_at ? new Date(selectedIncident.escalated_at).toLocaleString('en-IN') : '—'}</strong></div>
                  </div>
                  <div className="os-detail-section">
                    <h4>Escalation Reason</h4>
                    <p>{selectedIncident.escalation_reason}</p>
                  </div>
                  <div className="os-detail-section">
                    <h4>Summary</h4>
                    <p>{selectedIncident.summary || 'No summary available'}</p>
                  </div>
                  {selectedIncident.complaints?.length > 0 && (
                    <div className="os-detail-section">
                      <h4>Linked Complaints ({selectedIncident.complaints.length})</h4>
                      <ul className="os-complaint-list">
                        {selectedIncident.complaints.map(c => (
                          <li key={c.id}>{c.text}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="os-detail-empty">
                  <FileText size={36} />
                  <p>{t('os.selectIncident')}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OversightDashboard;
