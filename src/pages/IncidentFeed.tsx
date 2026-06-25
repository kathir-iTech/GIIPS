import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, AlertTriangle, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import type { Incident, SortField, SortDirection } from '../types';
import Header from '../components/Header';
import './IncidentFeed.css';

const IncidentFeed = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('priority_score');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');

  useEffect(() => {
    api.getIncidents(sortField).then(setIncidents).catch(err => setError(err.message)).finally(() => setLoading(false));
  }, [sortField]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedIncidents = [...incidents].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    const modifier = sortDirection === 'asc' ? 1 : -1;
    if (typeof aVal === 'number' && typeof bVal === 'number') return (aVal - bVal) * modifier;
    return String(aVal).localeCompare(String(bVal)) * modifier;
  });

  const filteredIncidents = filter === 'all' ? sortedIncidents : sortedIncidents.filter(i => i.priority_label.toLowerCase() === filter);

  const getPriorityIcon = (label: string) => {
    switch (label) {
      case 'Critical': return <AlertTriangle size={16} className="priority-icon critical" />;
      case 'High': return <AlertCircle size={16} className="priority-icon high" />;
      case 'Medium': return <Clock size={16} className="priority-icon medium" />;
      default: return <CheckCircle size={16} className="priority-icon low" />;
    }
  };

  if (loading) return <div className="page-loading">Loading incidents...</div>;
  if (error) return <div className="page-error">Error: {error}</div>;

  return (
    <div className="incident-feed-page">
      <Header title="Incident Feed" subtitle="Prioritized list of identified incidents" />
      <div className="page-content">
        <div className="feed-controls">
          <div className="filter-tabs">
            {(['all', 'critical', 'high', 'medium', 'low'] as const).map(f => (
              <button key={f} className={`filter-tab ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
          <div className="incident-count">{filteredIncidents.length} incidents</div>
        </div>

        <div className="incidents-table-container">
          <table className="incidents-table">
            <thead>
              <tr>
                <th></th>
                <th onClick={() => handleSort('incident_number')}>ID {sortField === 'incident_number' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}</th>
                <th onClick={() => handleSort('category')}>Category {sortField === 'category' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}</th>
                <th onClick={() => handleSort('cluster_size')}>Cluster Size {sortField === 'cluster_size' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}</th>
                <th onClick={() => handleSort('ward')}>Ward {sortField === 'ward' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}</th>
                <th onClick={() => handleSort('days_open')}>Days Open {sortField === 'days_open' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}</th>
                <th onClick={() => handleSort('priority_score')}>Priority Score {sortField === 'priority_score' && (sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}</th>
                <th>Priority</th>
                <th>Recommended Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredIncidents.map(incident => (
                <>
                  <tr key={incident.id} className={`incident-row priority-${incident.priority_label.toLowerCase()}`} onClick={() => setExpandedId(expandedId === incident.id ? null : incident.id)}>
                    <td className="expand-cell">
                      {expandedId === incident.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </td>
                    <td className="incident-id-cell">{incident.incident_number}</td>
                    <td>{incident.category}</td>
                    <td className="cluster-size-cell">{incident.cluster_size} complaints</td>
                    <td>{incident.ward}</td>
                    <td>{incident.days_open} days</td>
                    <td className="score-cell">{incident.priority_score}</td>
                    <td className="priority-cell">{getPriorityIcon(incident.priority_label)}<span>{incident.priority_label}</span></td>
                    <td className="action-cell">{incident.recommended_action}</td>
                  </tr>
                  {expandedId === incident.id && (
                    <tr className="expanded-row">
                      <td colSpan={9}>
                        <div className="expanded-content">
                          <div className="expanded-summary">
                            <h4>Summary</h4>
                            <p>{incident.summary}</p>
                          </div>
                          <div className="expanded-complaints">
                            <h4>Linked Complaints ({incident.complaints.length})</h4>
                            <table className="complaints-nested-table">
                              <thead>
                                <tr>
                                  <th>Complaint ID</th>
                                  <th>Date Received</th>
                                  <th>Similarity Score</th>
                                  <th>Text</th>
                                </tr>
                              </thead>
                              <tbody>
                                {incident.complaints.map(c => (
                                  <tr key={c.id}>
                                    <td>{c.complaint_number}</td>
                                    <td>{c.date_received}</td>
                                    <td className="similarity-score">{(c.similarity_score * 100).toFixed(1)}%</td>
                                    <td className="complaint-text">{c.text}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default IncidentFeed;
