import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import type { CitizenComplaint } from '../types';
import { FileText, MapPin, Calendar, Tag, AlertCircle, CheckCircle, Clock, Search, ChevronRight } from 'lucide-react';
import './MyComplaints.css';

const STATUS_STYLES: Record<string, string> = {
  open: 'status-open',
  'in-progress': 'status-progress',
  resolved: 'status-resolved',
  closed: 'status-closed',
};

const MyComplaints = () => {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [complaints, setComplaints] = useState<CitizenComplaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    let cancelled = false;
    if (!token) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    api.getMyComplaints(token)
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
  }, [token]);

  const filtered = complaints.filter(c => {
    const matchesSearch = !searchQuery.trim() ||
      (c.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.ward || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.predicted_category || '').toLowerCase().includes(searchQuery.toLowerCase());
    const incidentStatus = c.incident?.status || 'open';
    const matchesStatus = statusFilter === 'all' || incidentStatus === statusFilter;
    return matchesSearch && matchesStatus;
  });

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>Loading your complaints...</span></div>;
  if (error) return <div className="page-error">Error: {error}</div>;

  return (
    <div className="my-complaints-page">
      <Header title="My Complaints" subtitle="Track your submitted grievances" />
      <div className="page-content">
        <div className="toolbar">
          <div className="search-box">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              placeholder="Search by ID, title, ward..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="status-select">
            <option value="all">All Status</option>
            <option value="open">Open</option>
            <option value="in-progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        {filtered.length === 0 ? (
          <div className="empty-state">
            <FileText size={48} />
            <h3>No complaints found</h3>
            <p>You have not submitted any complaints yet, or none match your filters.</p>
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
                      <span>{c.title || 'Untitled Complaint'}</span>
                    </div>
                    <span className={`status-badge ${STATUS_STYLES[incidentStatus] || 'status-open'}`}>
                      {incidentStatus.replace('-', ' ')}
                    </span>
                  </div>
                  <p className="card-desc">{c.description}</p>
                  <div className="card-meta">
                    <span className="meta-item"><MapPin size={14} /> {c.ward || 'N/A'}</span>
                    <span className="meta-item"><Calendar size={14} /> {c.date_received ? new Date(c.date_received).toLocaleDateString('en-IN') : 'N/A'}</span>
                    <span className="meta-item"><AlertCircle size={14} /> {c.predicted_category || 'Uncategorized'}</span>
                  </div>
                  <div className="card-footer">
                    <div className="confidence-bar">
                      <div className="confidence-fill" style={{ width: `${Math.round((c.confidence || 0) * 100)}%` }}></div>
                      <span>AI Confidence: {Math.round((c.confidence || 0) * 100)}%</span>
                    </div>
                    <div className="duplicate-info">
                      {c.incident ? (
                        <span className="linked-incident">Linked: {c.incident.incident_number || 'Unknown'}</span>
                      ) : (
                        <span className="no-incident">No linked incident</span>
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
