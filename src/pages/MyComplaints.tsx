import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import Header from '../components/Header';
import type { CitizenComplaint } from '../types';
import { FileText, MapPin, Calendar, Tag, AlertCircle, Search, ChevronRight, X, Filter, Check, Clock, CheckCircle, Hourglass, BarChart3, Download } from 'lucide-react';
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

  const exportCSV = () => {
    const rows = filtered.map(c => {
      const status = c.incident?.status || 'open';
      const isResolved = ['resolved', 'closed'].includes(status);
      let resolvedDate = '';
      if (isResolved && c.date_received && c.incident?.days_open != null) {
        const d = new Date(c.date_received);
        d.setDate(d.getDate() + c.incident.days_open);
        resolvedDate = d.toLocaleDateString('en-IN');
      }
      return [
        c.id,
        `"${(c.title || '').replace(/"/g, '""')}"`,
        c.predicted_category || '',
        c.ward || '',
        status,
        c.date_received ? new Date(c.date_received).toLocaleDateString('en-IN') : '',
        resolvedDate,
        `"${(c.incident?.resolution_note || '').replace(/"/g, '""')}"`,
      ].join(',');
    });
    const header = 'ID,Title,Category,Ward,Status,Date Filed,Date Resolved,Resolution Note';
    const csv = '\uFEFF' + header + '\n' + rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `my-complaints-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    let mounted = true;

    const fetchComplaints = async (showLoader = false) => {
      if (!mounted) return;
      if (showLoader) setLoading(true);
      try {
        const res = await api.getMyComplaints();
        if (!mounted) return;
        setComplaints(Array.isArray(res.complaints) ? res.complaints : []);
      } catch (err: any) {
        if (!mounted) return;
        if (showLoader) setError(err.message);
      } finally {
        if (showLoader && mounted) setLoading(false);
      }
    };

    fetchComplaints(true);
    const interval = setInterval(() => fetchComplaints(false), 30000);
    return () => { mounted = false; clearInterval(interval); };
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

  const getActiveStages = (c: CitizenComplaint): number[] => {
    const st = c.incident?.status || 'pending';
    const hasOfficer = !!(c.assigned_officer?.name || c.assigned_officer?.phone);
    const hasIncident = st !== 'pending';
    const isResolved = ['resolved', 'pending_verification', 'closed'].includes(st);
    const isInProgress = isResolved || st === 'in-progress';
    const isRouted = isInProgress || (hasIncident && hasOfficer);
    const isVerified = isRouted || hasIncident;
    const active: number[] = [];
    if (true) active.push(0);
    if (isVerified) active.push(1);
    if (isRouted) active.push(2);
    if (isInProgress) active.push(3);
    if (isResolved) active.push(4);
    return active;
  };

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
          {complaints.length > 0 && (
            <button className="export-btn" onClick={exportCSV} title={t('myComplaints.exportCSV')}>
              <Download size={16} /> CSV
            </button>
          )}
        </div>

        {complaints.length > 0 && (
          <div className="citizen-stats">
            <div className="cs-card">
              <FileText size={16} />
              <span className="cs-value">{complaints.length}</span>
              <span className="cs-label">{t('myComplaints.statTotal')}</span>
            </div>
            <div className="cs-card">
              <CheckCircle size={16} />
              <span className="cs-value">{complaints.filter(c => ['resolved', 'closed'].includes(c.incident?.status || '')).length}</span>
              <span className="cs-label">{t('myComplaints.statResolved')}</span>
            </div>
            <div className="cs-card">
              <Hourglass size={16} />
              <span className="cs-value">{complaints.filter(c => !['resolved', 'closed'].includes(c.incident?.status || '') && c.incident?.status).length}</span>
              <span className="cs-label">{t('myComplaints.statPending')}</span>
            </div>
            <div className="cs-card">
              <BarChart3 size={16} />
              <span className="cs-value">
                {(() => {
                  const resolved = complaints.filter(c => ['resolved', 'closed'].includes(c.incident?.status || '') && c.incident?.days_open != null);
                  if (resolved.length === 0) return '—';
                  const avg = resolved.reduce((s, c) => s + (c.incident!.days_open!), 0) / resolved.length;
                  return avg.toFixed(1) + 'd';
                })()}
              </span>
              <span className="cs-label">{t('myComplaints.statAvgResolution')}</span>
            </div>
          </div>
        )}

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
                    <div className="sc-steps">
                      {[0, 1, 2, 3, 4].map(i => (
                        <div key={i} className={`sc-step ${getActiveStages(c).includes(i) ? 'done' : ''}`}>
                          {getActiveStages(c).includes(i) ? <Check size={10} /> : null}
                        </div>
                      ))}
                    </div>
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
