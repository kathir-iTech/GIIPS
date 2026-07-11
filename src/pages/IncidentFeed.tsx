import { useState, useEffect, useMemo } from 'react';
import { ChevronDown, ChevronUp, TriangleAlert as AlertTriangle, CircleCheck as CheckCircle, Clock, CircleAlert as AlertCircle, Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../services/api';
import type { Incident, SortField, SortDirection } from '../types';
import Header from '../components/Header';
import './IncidentFeed.css';

const PAGE_SIZE = 10;

const IncidentFeed = () => {
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

  useEffect(() => {
    let cancelled = false;

    const fetchIncidents = async (showLoader = false) => {
      if (cancelled) return;
      try {
        const data = await api.getIncidents(sortField);
        if (!cancelled) setAllIncidents(data || []);
      } catch (e) {
        if (!cancelled) {
          if (showLoader) {
            setError('Failed to load incidents. Please try again.');
          }
          console.error('Failed to fetch incidents:', e);
        }
      } finally {
        if (showLoader && !cancelled) setLoading(false);
      }
    };

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

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>Loading incidents...</span></div>;
  if (error) return <div className="page-error">Error: {error}</div>;

  return (
    <div className="incident-feed-page">
      <Header title="Incident Feed" subtitle="Prioritized list of identified incidents" />
      <div className="page-content">
        <div className="feed-toolbar">
          <div className="search-box">
            <Search size={18} className="search-icon" />
            <input type="text" placeholder="Search by ID, ward, category..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
          </div>
          <div className="filter-group">
            <Filter size={16} />
            <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value as typeof priorityFilter)}>
              <option value="all">All Priorities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
              <option value="all">All Categories</option>
              {categories.map(cat => <option key={cat} value={cat}>{cat}</option>)}
            </select>
          </div>
          <div className="results-count">{filteredAndSorted.length} incidents</div>
        </div>

        <div className="incidents-table-container">
          <table className="incidents-table">
            <thead>
              <tr>
                <th className="expand-col"></th>
                <th onClick={() => handleSort('incident_number')} className={sortField === 'incident_number' ? 'active' : ''}>
                  Incident ID {sortField === 'incident_number' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </th>
                <th onClick={() => handleSort('category')} className={sortField === 'category' ? 'active' : ''}>
                  Category {sortField === 'category' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </th>
                <th>Department</th>
                <th onClick={() => handleSort('cluster_size')} className={sortField === 'cluster_size' ? 'active' : ''}>
                  Cluster {sortField === 'cluster_size' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </th>
                <th onClick={() => handleSort('ward')} className={sortField === 'ward' ? 'active' : ''}>
                  Ward {sortField === 'ward' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </th>
                <th onClick={() => handleSort('days_open')} className={sortField === 'days_open' ? 'active' : ''} >
                  Days {sortField === 'days_open' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </th>
                <th onClick={() => handleSort('priority_score')} className={sortField === 'priority_score' ? 'active' : ''}>
                  Score {sortField === 'priority_score' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </th>
                <th>Priority</th>
                <th className="action-col">Recommended Action</th>
              </tr>
            </thead>
            <tbody>
              {pagedIncidents.length === 0 ? (
                  <tr className="empty-row">
                    <td colSpan={10}>
                    <div className="empty-state">
                      <AlertCircle size={32} />
                      <p>No incidents match your current filters.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                pagedIncidents.map(incident => (
                  <tr key={incident.id} className={`incident-row priority-${incident.priority_label?.toLowerCase()}`} onClick={() => setExpandedId(expandedId === incident.id ? null : incident.id)}>
                    <td className="expand-cell">{expandedId === incident.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</td>
                    <td className="incident-id">{incident.incident_number}</td>
                    <td><span className="category-badge">{incident.category}</span></td>
                    <td className="dept-cell">{incident.department || incident.category}</td>
                    <td className="cluster-size"><span className="cluster-badge">{incident.cluster_size}</span></td>
                    <td className="ward-cell">{incident.ward?.replace('Ward ', 'W').split(' - ')[0]}</td>
                    <td className="days-cell">{incident.days_open}d</td>
                    <td className="score-cell"><span className="score-badge">{incident.priority_score}</span></td>
                    <td className="priority-cell">{getPriorityIcon(incident.priority_label || 'Low')}<span>{incident.priority_label || 'Low'}</span></td>
                    <td className="action-cell" title={incident.recommended_action}>{incident.recommended_action}</td>
                  </tr>
                ))
              )}
              {expandedId && pagedIncidents.map(incident => expandedId === incident.id && (
                <tr key={`expanded-${incident.id}`} className="expanded-row">
                  <td colSpan={10}>
                    <div className="expanded-content">
                      <div className="expanded-left">
                        <div className="detail-block">
                          <h4>Summary</h4>
                          <p>{incident.summary}</p>
                        </div>
                        <div className="detail-block">
                          <h4>Clustering Reasoning</h4>
                          <p className="reasoning">
                            {incident.complaints && incident.complaints.length > 0 && incident.complaints[0]?.similarity_score
                              ? `Complaints clustered with ${(incident.complaints[0].similarity_score * 100).toFixed(0)}% average similarity.`
                              : 'Clustering based on semantic similarity of reported issues.'}
                          </p>
                        </div>
                      </div>
                      <div className="expanded-right">
                        <h4>Linked Complaints ({incident.complaints?.length || 0})</h4>
                        <div className="complaints-list">
                          {(incident.complaints?.slice(0, 5) ?? []).map(c => (
                            <div key={c.id} className="complaint-item">
                              <div className="complaint-header">
                                <span className="complaint-id">{c.complaint_number}</span>
                                <span className="complaint-date">{c.date_received}</span>
                                <div className="similarity-indicator"><div className="sim-bar" style={{ width: `${(c.similarity_score || 0) * 100}%` }}></div><span>{((c.similarity_score || 0) * 100).toFixed(0)}%</span></div>
                              </div>
                              <p className="complaint-text">{c.text}</p>
                            </div>
                          ))}
                          {incident.complaints && incident.complaints.length > 5 && <div className="more-complaints">+{incident.complaints.length - 5} more complaints</div>}
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
            <button className="page-btn" disabled={currentPage === 1} onClick={() => setCurrentPage(p => p - 1)}><ChevronLeft size={16} /> Prev</button>
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
            <button className="page-btn" disabled={currentPage === totalPages} onClick={() => setCurrentPage(p => p + 1)}>Next <ChevronRight size={16} /></button>
          </div>
        )}
      </div>
    </div>
  );
};

export default IncidentFeed;
