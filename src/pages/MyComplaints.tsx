import { useState, useEffect, useCallback } from 'react';
import { useDashboardSocket } from '../hooks/useDashboardSocket';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import Header from '../components/Header';
import HelpWidget from '../components/HelpWidget';
import { getSLAStatus, getSLAStatusLabel } from '../utils/sla';
import type { CitizenComplaint } from '../types';
import { FileText, MapPin, Calendar, Tag, AlertCircle, Search, ChevronRight, X, Filter, Check, Clock, CheckCircle, Hourglass, BarChart3, Download, Activity, Camera } from 'lucide-react';
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
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [streakBadge, setStreakBadge] = useState<string | null>(null);
  const [peakPeriod, setPeakPeriod] = useState<string | null>(null);
  const [photoUrls, setPhotoUrls] = useState<Record<string, string>>({});
  const [followUpLoading, setFollowUpLoading] = useState<Record<string, boolean>>({});
  const [followUpSent, setFollowUpSent] = useState<Record<string, boolean>>({});
  const [compareMode, setCompareMode] = useState(false);
  const [selectedForCompare, setSelectedForCompare] = useState<any[]>([]);

  const handleFollowUp = async (complaint: CitizenComplaint) => {
    const key = `follow_up_${complaint.id}`;
    if (localStorage.getItem(key)) return;
    setFollowUpLoading(prev => ({ ...prev, [complaint.id]: true }));
    try {
      await api.post(`/complaints/${complaint.id}/updates`, { message: 'Follow-up: Status check requested by citizen.' });
      setFollowUpSent(prev => ({ ...prev, [complaint.id]: true }));
      localStorage.setItem(key, Date.now().toString());
    } catch {}
    setFollowUpLoading(prev => ({ ...prev, [complaint.id]: false }));
  };

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
    const header = t('myComplaints.csvHeaders');
    const csv = '\uFEFF' + header + '\n' + rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `my-complaints-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const fetchComplaints = useCallback(async (showLoader = false) => {
    if (showLoader) setLoading(true);
    try {
      const res = await api.getMyComplaints();
      const complaintsData = Array.isArray(res.complaints) ? res.complaints : [];
      setComplaints(complaintsData);
      const urls: Record<string, string> = {};
      await Promise.all(complaintsData.filter((c: any) => c.image_path && !c.image_path.startsWith('http')).map(async (c: any) => {
        try {
          const photoRes = await api.getComplaintPhoto(c.id);
          if (photoRes.imageUrl) urls[c.id] = photoRes.imageUrl;
        } catch {}
      }));
      complaintsData.filter((c: any) => c.image_path?.startsWith('http')).forEach((c: any) => { urls[c.id] = c.image_path; });
      setPhotoUrls(urls);
    } catch (err: any) {
      if (showLoader) setError(err.message);
    } finally {
      if (showLoader) setLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    const fetchWithMount = async (showLoader: boolean) => {
      if (!mounted) return;
      await fetchComplaints(showLoader);
    };
    fetchWithMount(true);
    const interval = setInterval(() => fetchWithMount(false), 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, [fetchComplaints]);

  useDashboardSocket({
    onEvent: () => { fetchComplaints(false); },
  });

  useEffect(() => {
    if (!searchQuery.trim()) { setSearchResults(null); return; }
    const timer = setTimeout(async () => {
      try { setSearchResults(await api.searchComplaints(searchQuery)); } catch { setSearchResults([]); }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    const monthSet = new Set(complaints.map(c => c.date_received ? new Date(c.date_received).toISOString().slice(0, 7) : ''));
    const months = Array.from(monthSet).sort();
    let consecutive = 1;
    for (let i = 1; i < months.length; i++) {
      const prev = new Date(months[i-1] + '-01');
      const curr = new Date(months[i] + '-01');
      if ((curr.getFullYear() - prev.getFullYear()) * 12 + (curr.getMonth() - prev.getMonth()) === 1) {
        consecutive++;
        if (consecutive >= 3) break;
      } else consecutive = 1;
    }
    setStreakBadge(consecutive >= 3 ? t('myComplaints.activeReporter') : null);

    const hourCounts = [0, 0, 0, 0];
    complaints.forEach(c => {
      if (!c.date_received) return;
      const h = new Date(c.date_received).getHours();
      if (h >= 5 && h < 12) hourCounts[0]++;
      else if (h >= 12 && h < 17) hourCounts[1]++;
      else if (h >= 17 && h < 21) hourCounts[2]++;
      else hourCounts[3]++;
    });
    const periods = ['morning', 'afternoon', 'evening', 'night'];
    setPeakPeriod(periods[hourCounts.indexOf(Math.max(...hourCounts))]);
  }, [complaints]);

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
        {(streakBadge || peakPeriod) && (
          <div className="insight-badges">
            {streakBadge && <span className="streak-badge"><Activity size={14} /> {streakBadge}</span>}
            {peakPeriod && <span className="peak-period-badge"><Clock size={14} /> {t('myComplaints.usually', { period: t('myComplaints.' + peakPeriod) })}</span>}
            {(() => {
              const total = complaints.length;
              const resolved = complaints.filter(c => c.incident?.status === 'closed' || c.incident?.status === 'resolved').length;
              const verified = complaints.filter(c => c.citizen_rating != null).length;
              const appealed = complaints.filter(c => (c.incident as any)?.appealed).length;
              let score = total > 0 ? (resolved / total) * 100 : 0;
              score += Math.min(verified * 5, 20);
              score = Math.min(Math.round(score), 100);
              const impactLevel = score >= 70 ? 'myComplaints.impactHigh' : score >= 40 ? 'myComplaints.impactMedium' : 'myComplaints.impactLow';
              return <span className="impact-score-badge"><BarChart3 size={14} /> {t('myComplaints.impactScore', { score, label: t(impactLevel) })}</span>;
            })()}
          </div>
        )}
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
              <Download size={16} /> {t('myComplaints.exportCSV')}
            </button>
          )}
          <button className="btn btn-secondary" onClick={() => { setCompareMode(!compareMode); setSelectedForCompare([]); }}>
            {compareMode ? t('myComplaints.compareExit') : t('myComplaints.compare')}
          </button>
        </div>

        {searchResults !== null && (
          <div className="search-results-dropdown">
            <div className="search-results-header">{t('myComplaints.searchResultsHeader', { count: searchResults.length })}</div>
            {searchResults.length === 0 ? (
              <div className="search-results-empty">{t('myComplaints.noSearchResults')}</div>
            ) : (
              searchResults.slice(0, 10).map((r: any) => (
                <div key={r.id} className="search-result-item" onClick={() => navigate(`/complaint/${r.id}`)}>
                  <span className="search-result-title">{r.title}</span>
                  <span className="search-result-meta">{r.ward} — {r.predicted_category}</span>
                  <span className="search-result-status">{r.status}</span>
                </div>
              ))
            )}
          </div>
        )}

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
                  return avg.toFixed(1) + t('myComplaints.daysUnit');
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
          <>
          {compareMode && selectedForCompare.length === 2 && (
            <div className="compare-panel" style={{ background: '#1e293b', borderRadius: '12px', padding: '1.5rem', marginBottom: '1.5rem', border: '1px solid #334155' }}>
              <h3 style={{ marginBottom: '1rem' }}>{t('myComplaints.compareTitle')}</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                {selectedForCompare.map((sc, si) => (
                  <div key={si} style={{ background: '#0f172a', borderRadius: '8px', padding: '1rem' }}>
                    <p><strong>ID:</strong> {sc.id}</p>
                    <p><strong>{t('myComplaints.compareTitleField')}:</strong> {sc.title || t('common.untitled')}</p>
                    <p><strong>{t('myComplaints.compareCategory')}:</strong> {sc.predicted_category || t('common.uncategorized')}</p>
                    <p><strong>{t('myComplaints.compareStatus')}:</strong> {t(STATUS_KEY[sc.incident?.status || 'open'])}</p>
                    <p><strong>{t('myComplaints.compareWard')}:</strong> {sc.ward || t('common.na')}</p>
                    <p><strong>{t('myComplaints.compareDate')}:</strong> {sc.date_received ? new Date(sc.date_received).toLocaleDateString('en-IN') : t('common.na')}</p>
                    <p><strong>{t('myComplaints.compareDesc')}:</strong> {sc.description?.slice(0, 200)}{sc.description?.length > 200 ? '…' : ''}</p>
                    {sc.incident?.days_open != null && <p><strong>{t('myComplaints.compareDaysOpen')}:</strong> {sc.incident.days_open}d</p>}
                    <p><strong>{t('myComplaints.compareConfidence')}:</strong> {getConfidenceLabel(sc.confidence, t)}</p>
                  </div>
                ))}
              </div>
              <button className="btn btn-secondary" style={{ marginTop: '1rem' }} onClick={() => setSelectedForCompare([])}>{t('myComplaints.compareClear')}</button>
            </div>
          )}
          <div className="complaints-list">
            {filtered.map(c => {
              const incidentStatus = c.incident?.status || 'open';
              const isSelected = selectedForCompare.find(s => s.id === c.id);
              return (
                  <div key={c.id} className="complaint-card" onClick={() => { if (compareMode) return; navigate(`/complaint/${c.id}`); }}
                    style={compareMode && isSelected ? { borderColor: '#3b82f6' } : {}}>
                    {compareMode && (
                      <div style={{ position: 'absolute', top: '8px', left: '8px', zIndex: 2 }}>
                        <input type="checkbox" checked={!!isSelected} onChange={() => {
                          if (isSelected) {
                            setSelectedForCompare(prev => prev.filter(s => s.id !== c.id));
                          } else if (selectedForCompare.length < 2) {
                            setSelectedForCompare(prev => [...prev, c]);
                          }
                        }} style={{ width: '20px', height: '20px', cursor: 'pointer' }} />
                      </div>
                    )}
                    <div className="complaint-photo-thumb">
                      {photoUrls[c.id] ? (
                        <img src={photoUrls[c.id]} alt="" className="complaint-thumb-img" />
                      ) : (
                        <Camera size={18} className="complaint-thumb-placeholder" />
                      )}
                    </div>
                    <div className="card-header">
                      <div className="card-title">
                        <Tag size={16} />
                        <span>{c.title || t('common.untitled')}</span>
                      </div>
                      <span className={`status-badge ${STATUS_STYLES[incidentStatus] || 'status-open'}`}>
                        {t(STATUS_KEY[incidentStatus] || 'common.status.open')}
                      </span>
                      {c.incident?.days_open != null && (
                        <span className={`sla-badge sla-${getSLAStatus(c.incident.days_open, c.ward)}`}>
                          {getSLAStatusLabel(getSLAStatus(c.incident.days_open, c.ward), t)}
                        </span>
                      )}
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
                  {c.incident?.days_open != null && c.incident.days_open > 15 && !['resolved', 'closed', 'pending_verification'].includes(incidentStatus) && !localStorage.getItem(`follow_up_${c.id}`) && !followUpSent[c.id] && (
                    <button className="nudge-btn" onClick={(e) => { e.stopPropagation(); handleFollowUp(c); }} disabled={followUpLoading[c.id]}>
                      {followUpLoading[c.id] ? t('myComplaints.followUpSending') : t('myComplaints.followUp')}
                    </button>
                  )}
                  {followUpSent[c.id] && <span className="follow-up-sent">{t('myComplaints.followUpSent')}</span>}
                  <ChevronRight size={18} className="arrow-icon" />
                </div>
              );
            })}
          </div>
        </>)}
      </div>
      <HelpWidget />
    </div>
  );
};

export default MyComplaints;
