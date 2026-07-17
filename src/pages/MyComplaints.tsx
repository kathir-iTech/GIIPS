import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import Header from '../components/Header';
import type { CitizenComplaint } from '../types';
import { FileText, MapPin, Calendar, Tag, AlertCircle, CheckCircle, Clock, Search, ChevronRight, X, Filter } from 'lucide-react';
import './MyComplaints.css';

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

const MyComplaints = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [complaints, setComplaints] = useState<CitizenComplaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const resetFilters = () => {
    setSearchQuery('');
    setStatusFilter('all');
    setDateFrom('');
    setDateTo('');
  };

  const hasActiveFilters = searchQuery.trim() || statusFilter !== 'all' || dateFrom || dateTo;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.getMyComplaints()
      .then(res => {
        if (cancelled) return;
        setComplaints(Array.isArray(res.complaints) ? res.complaints : []);
      })
      .catch(err => {
        if (cancelled) return;
        setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const filtered = complaints.filter(c => {
    const matchesSearch = !searchQuery.trim() ||
      (c.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.ward || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.predicted_category || '').toLowerCase().includes(searchQuery.toLowerCase());
    const incidentStatus = c.incident?.status || 'open';
    const matchesStatus = statusFilter === 'all' || incidentStatus === statusFilter;
    const complaintDate = c.date_received ? new Date(c.date_received) : null;
    const matchesDateFrom = !dateFrom || (complaintDate && complaintDate >= new Date(dateFrom));
    const matchesDateTo = !dateTo || (complaintDate && complaintDate <= new Date(dateTo + 'T23:59:59'));
    return matchesSearch && matchesStatus && matchesDateFrom && matchesDateTo;
  });

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>{t('myComplaints.loading')}</span></div>;
  if (error) return <div className="page-error">{t('common.error')}: {error}</div>;

  return (
    <div className="my-complaints-page">
      <Header title={t('myComplaints.headerTitle')} subtitle={t('myComplaints.headerSubtitle')} />
      <div className="page-content">
        <div className="toolbar">
          <div className="search-box">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              placeholder={t('myComplaints.searchPlaceholder')}
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="filter-group">
            <Filter size={16} />
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="status-select">
              <option value="all">{t('common.status.all')}</option>
              <option value="open">{t('common.status.open')}</option>
              <option value="in-progress">{t('common.status.inProgress')}</option>
              <option value="pending_verification">{t('common.status.pendingVerification')}</option>
              <option value="resolved">{t('common.status.resolved')}</option>
              <option value="closed">{t('common.status.closed')}</option>
            </select>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="date-input"
              aria-label={t('myComplaints.dateFrom')}
            />
            <span className="date-separator">—</span>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              className="date-input"
              aria-label={t('myComplaints.dateTo')}
            />
          </div>
          {hasActiveFilters && (
            <button className="reset-btn" onClick={resetFilters} title={t('myComplaints.resetFilters')}>
              <X size={16} /> {t('myComplaints.resetFilters')}
            </button>
          )}
        </div>

        {filtered.length === 0 ? (
          <div className="empty-state">
            <FileText size={48} />
            <h3>{t('myComplaints.emptyTitle')}</h3>
            <p>{t('myComplaints.emptyBody')}</p>
          </div>
        ) : (
          <div className="complaints-list">
            {filtered.map(c => {
              const incidentStatus = c.incident?.status || 'open';
              return (
                <div key={c.id} className="complaint-card" onClick={() => navigate(`/complaint/${c.id}`)}>
                  <div className="card-header">
                    <div className="card-title">
                      <Tag size={16} />
                      <span>{c.title || t('common.untitled')}</span>
                    </div>
                    <span className={`status-badge ${STATUS_STYLES[incidentStatus] || 'status-open'}`}>
                      {t(STATUS_KEY[incidentStatus] || 'common.status.open')}
                    </span>
                  </div>
                  <p className="card-desc">{c.description}</p>
                  <div className="card-meta">
                    <span className="meta-item"><MapPin size={14} /> {c.ward || t('common.na')}</span>
                    <span className="meta-item"><Calendar size={14} /> {c.date_received ? new Date(c.date_received).toLocaleDateString('en-IN') : t('common.na')}</span>
                    <span className="meta-item"><AlertCircle size={14} /> {c.predicted_category || t('common.uncategorized')}</span>
                  </div>
                  {c.assigned_officer?.name && (
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
                      {t('myComplaints.assignedTo', { name: c.assigned_officer.name })}
                    </div>
                  )}
                  <div className="card-footer">
                    <div className="confidence-bar">
                      <div className="confidence-fill" style={{ width: `${Math.round((c.confidence || 0) * 100)}%` }}></div>
                      <span>{t('myComplaints.confidenceLabel')} {getConfidenceLabel(c.confidence, t)}</span>
                    </div>
                    <div className="duplicate-info">
                      {c.incident ? (
                        <span className="linked-incident">{t('common.groupedWithSimilar')}</span>
                      ) : (
                        <span className="no-incident">{t('myComplaints.standalone')}</span>
                      )}
                    </div>
                  </div>
                  <ChevronRight size={18} className="arrow-icon" />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default MyComplaints;
