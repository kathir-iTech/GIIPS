import { useState, useEffect, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronUp, TriangleAlert as AlertTriangle, CircleCheck as CheckCircle, Clock, CircleAlert as AlertCircle, Search, Filter, ChevronLeft, ChevronRight, ArrowUpDown, GitMerge } from 'lucide-react';
import { api } from '../services/api';
import type { Incident, SortField, SortDirection } from '../types';
import Header from '../components/Header';
import { getDeptI18nKey } from '../data/departments';
import { AgingBadge } from '../components/AgingBadge';
import './IncidentFeed.css';

const PAGE_SIZE = 10;

const IncidentFeed = () => {
  const { t } = useTranslation();
  const [allIncidents, setAllIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('priority_score');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [priorityFilter, setPriorityFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [mergeError, setMergeError] = useState<string | null>(null);
  const [splitError, setSplitError] = useState<string | null>(null);

  const handleMerge = useCallback(async () => {
    const ids = Array.from(selectedIds);
    if (ids.length < 2) return;
    setMergeError(null);
    try {
      await api.mergeIncidents(ids);
      setSelectedIds(new Set());
      setExpandedId(null);
      const data = await api.getIncidents(sortField);
      setAllIncidents(data || []);
    } catch (err: any) {
      setMergeError(err.message || t('incidents.catch.mergeFailed'));
    }
  }, [selectedIds, sortField]);

  const handleSplit = useCallback(async (incidentId: string, complaintId: string) => {
    setSplitError(null);
    try {
      await api.splitComplaint(incidentId, complaintId);
      setExpandedId(null);
      const data = await api.getIncidents(sortField);
      setAllIncidents(data || []);
    } catch (err: any) {
      setSplitError(err.message || t('incidents.catch.splitFailed'));
    }
  }, [sortField]);

  useEffect(() => {
    let cancelled = false;

    const fetchIncidents = async (showLoader = false) => {
      if (cancelled) return;
      try {
        const data = await api.getIncidents(sortField);
        if (!cancelled) {
          setAllIncidents(data || []);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          if (showLoader) {
            setError(t('incidents.loadError'));
          }
          console.error('Failed to fetch incidents:', e);
        }
      } finally {
        if (showLoader && !cancelled) setLoading(false);
      }
    };

    setMergeError(null);
    setSplitError(null);

    fetchIncidents(true);
    const interval = setInterval(() => fetchIncidents(false), 30000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  const categories = useMemo(() => {
    const cats = new Set(allIncidents.map(i => i.category));
    return Array.from(cats).sort();
  }, [allIncidents]);

  const filteredAndSorted = useMemo(() => {
    let result = [...allIncidents];
    if (priorityFilter !== 'all') result = result.filter(i => i.priority_label?.toLowerCase() === priorityFilter);
    if (categoryFilter !== 'all') result = result.filter(i => i.category === categoryFilter);
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(i =>
        (i.incident_number || '').toLowerCase().includes(q) ||
        (i.ward || '').toLowerCase().includes(q) ||
        (i.summary || '').toLowerCase().includes(q) ||
        (i.category || '').toLowerCase().includes(q)
      );
    }
    result.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      const modifier = sortDirection === 'asc' ? 1 : -1;
      if (typeof aVal === 'number' && typeof bVal === 'number') return (aVal - bVal) * modifier;
      return String(aVal || '').localeCompare(String(bVal || '')) * modifier;
    });
    return result;
  }, [allIncidents, priorityFilter, categoryFilter, searchQuery, sortField, sortDirection]);

  const totalPages = Math.ceil(filteredAndSorted.length / PAGE_SIZE);
  const pagedIncidents = filteredAndSorted.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  useEffect(() => { setCurrentPage(1); }, [priorityFilter, categoryFilter, searchQuery]);

  const handleSort = (field: SortField) => {
    if (sortField === field) setSortDirection(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDirection('desc'); }
  };

  const getPriorityIcon = (label: string) => {
    switch (label) {
      case 'Critical': return <AlertTriangle size={16} className="priority-icon critical" />;
      case 'High': return <AlertCircle size={16} className="priority-icon high" />;
      case 'Medium': return <Clock size={16} className="priority-icon medium" />;
      default: return <CheckCircle size={16} className="priority-icon low" />;
    }
  };

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>{t('incidents.loading')}</span></div>;
  if (error) return <div className="page-error">{t('incidents.errorPrefix')}{error}</div>;

  return (
    <div className="incident-feed-page">
      <Header title={t('incidents.header.title')} subtitle={t('incidents.header.subtitle')} />
      <div className="page-content">
        <div className="feed-toolbar">
          <div className="search-box">
            <Search size={18} className="search-icon" />
            <input type="text" placeholder={t('incidents.searchPlaceholder')} value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
          </div>
          <div className="filter-group">
            <Filter size={16} />
            <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value as typeof priorityFilter)}>
              <option value="all">{t('incidents.allPriorities')}</option>
              <option value="critical">{t('common.priority.critical')}</option>
              <option value="high">{t('common.priority.high')}</option>
              <option value="medium">{t('common.priority.medium')}</option>
              <option value="low">{t('common.priority.low')}</option>
            </select>
            <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
              <option value="all">{t('incidents.allCategories')}</option>
              {categories.map(cat => <option key={cat} value={cat}>{cat}</option>)}
            </select>
          </div>
          <div className="results-count">{t('incidents.resultsCount', { count: filteredAndSorted.length })}</div>
          <button
            className={`sort-age-btn ${sortField === 'days_open' ? 'active' : ''}`}
            onClick={() => handleSort('days_open')}
            title={t('incidents.sortByDays')}
          >
            <ArrowUpDown size={14} /> {t('incidents.oldest')}
          </button>
          {selectedIds.size >= 2 && (
            <button className="merge-btn" onClick={handleMerge} title={t('incidents.mergeTitle')}>
              <GitMerge size={14} /> {t('incidents.merge')} {selectedIds.size}
            </button>
          )}
        </div>
        {mergeError && <div className="feed-error"><AlertCircle size={14} /> {mergeError} <button onClick={() => setMergeError(null)}>x</button></div>}
        {splitError && <div className="feed-error"><AlertCircle size={14} /> {splitError} <button onClick={() => setSplitError(null)}>x</button></div>}

        <div className="incidents-table-container">
          <table className="incidents-table">
            <thead>
              <tr>
                <th className="select-col"><input type="checkbox" onChange={e => { if (e.target.checked) setSelectedIds(new Set(pagedIncidents.map(i => i.id))); else setSelectedIds(new Set()); }} checked={selectedIds.size === pagedIncidents.length && pagedIncidents.length > 0} /></th>
                <th className="expand-col"></th>
                <th onClick={() => handleSort('incident_number')} className={sortField === 'incident_number' ? 'active' : ''}>
                  {t('incidents.colIncidentId')} {sortField === 'incident_number' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </th>
                <th onClick={() => handleSort('category')} className={sortField === 'category' ? 'active' : ''}>
                  {t('incidents.colCategory')} {sortField === 'category' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </th>
                <th>{t('incidents.colDepartment')}</th>
                <th onClick={() => handleSort('cluster_size')} className={sortField === 'cluster_size' ? 'active' : ''}>
                  {t('incidents.colCluster')} {sortField === 'cluster_size' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </th>
                <th onClick={() => handleSort('ward')} className={sortField === 'ward' ? 'active' : ''}>
                  {t('incidents.colWard')} {sortField === 'ward' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </th>
                <th onClick={() => handleSort('days_open')} className={sortField === 'days_open' ? 'active' : ''} >
                  {t('incidents.colDays')} {sortField === 'days_open' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </th>
                <th onClick={() => handleSort('priority_score')} className={sortField === 'priority_score' ? 'active' : ''}>
                  {t('incidents.colScore')} {sortField === 'priority_score' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </th>
                <th>{t('incidents.colPriority')}</th>
                <th className="action-col">{t('incidents.colRecommendedAction')}</th>
              </tr>
            </thead>
            <tbody>
              {pagedIncidents.length === 0 ? (
                  <tr className="empty-row">
                    <td colSpan={10}>
                    <div className="empty-state">
                      <AlertCircle size={32} />
                      <p>{t('incidents.emptyFiltered')}</p>
                    </div>
                  </td>
                </tr>
              ) : (
                pagedIncidents.map(incident => (
                  <tr key={incident.id} className={`incident-row priority-${incident.priority_label?.toLowerCase()} ${selectedIds.has(incident.id) ? 'selected' : ''}`}>
                    <td className="select-cell" onClick={e => e.stopPropagation()}><input type="checkbox" checked={selectedIds.has(incident.id)} onChange={() => setSelectedIds(prev => { const next = new Set(prev); if (next.has(incident.id)) next.delete(incident.id); else next.add(incident.id); return next; })} /></td>
                    <td className="expand-cell" onClick={() => setExpandedId(expandedId === incident.id ? null : incident.id)}>{expandedId === incident.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</td>
                    <td className="incident-id">{incident.incident_number}</td>
                    <td><span className="category-badge">{incident.category}</span></td>
                    <td className="dept-cell">{t(getDeptI18nKey(incident.department || incident.category))}</td>
                    <td className="cluster-size"><span className="cluster-badge">{incident.cluster_size}</span></td>
                    <td className="ward-cell">{incident.ward?.replace('Ward ', 'W').split(' - ')[0]}</td>
                    <td className="days-cell"><AgingBadge daysOpen={incident.days_open} /></td>
                    <td className="score-cell"><span className="score-badge">{incident.priority_score}</span></td>
                    <td className="priority-cell">{getPriorityIcon(incident.priority_label || 'Low')}<span>{incident.priority_label || t('common.priority.low')}</span></td>
                    <td className="action-cell" title={incident.recommended_action || ''}>{incident.recommended_action}</td>
                  </tr>
                ))
              )}
              {expandedId && pagedIncidents.map(incident => expandedId === incident.id && (
                <tr key={`expanded-${incident.id}`} className="expanded-row">
                  <td colSpan={11}>
                    <div className="expanded-content">
                      <div className="expanded-left">
                        <div className="detail-block">
                          <h4>{t('incidents.summary')}</h4>
                          <p>{incident.summary}</p>
                        </div>
                        <div className="detail-block">
                          <h4>{t('incidents.clusteringReasoning')}</h4>
                          <p className="reasoning">
                            {incident.complaints && incident.complaints.length > 0 && incident.complaints[0]?.similarity_score
                              ? t('incidents.clusteredWithSimilarity', { score: (incident.complaints[0].similarity_score * 100).toFixed(0) })
                              : t('incidents.clusteringDefaultReason')}
                          </p>
                        </div>
                      </div>
                      <div className="expanded-right">
                        <h4>{t('incidents.linkedComplaints', { count: incident.complaints?.length || 0 })}</h4>
                        <div className="complaints-list">
                          {(incident.complaints?.slice(0, 5) ?? []).map(c => (
                            <div key={c.id} className="complaint-item">
                              <div className="complaint-header">
                                <span className="complaint-id">{c.complaint_number}</span>
                                <span className="complaint-date">{c.date_received}</span>
                                <div className="similarity-indicator"><div className="sim-bar" style={{ width: `${(c.similarity_score || 0) * 100}%` }}></div><span>{((c.similarity_score || 0) * 100).toFixed(0)}%</span></div>
                                <button className="split-btn" onClick={(e) => { e.stopPropagation(); handleSplit(incident.id, c.id); }} title={t('incidents.splitTitle')}>{t('incidents.split')}</button>
                              </div>
                              <p className="complaint-text">{c.text}</p>
                            </div>
                          ))}
                          {incident.complaints && incident.complaints.length > 5 && <div className="more-complaints">{t('incidents.moreComplaints', { count: incident.complaints.length - 5 })}</div>}
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="pagination">
            <button className="page-btn" disabled={currentPage === 1} onClick={() => setCurrentPage(p => p - 1)}><ChevronLeft size={16} /> {t('incidents.prev')}</button>
            <div className="page-numbers">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum: number;
                if (totalPages <= 5) pageNum = i + 1;
                else if (currentPage <= 3) pageNum = i + 1;
                else if (currentPage >= totalPages - 2) pageNum = totalPages - 4 + i;
                else pageNum = currentPage - 2 + i;
                return <button key={i} className={`page-num ${currentPage === pageNum ? 'active' : ''}`} onClick={() => setCurrentPage(pageNum)}>{pageNum}</button>;
              })}
            </div>
            <button className="page-btn" disabled={currentPage === totalPages} onClick={() => setCurrentPage(p => p + 1)}>{t('incidents.next')} <ChevronRight size={16} /></button>
          </div>
        )}
      </div>
    </div>
  );
};

export default IncidentFeed;
