import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Search, Filter, Clock, User, Shield, FileText } from 'lucide-react';
import './Admin.css';

interface AuditLog {
  id: string;
  timestamp: string;
  user: string;
  role: string;
  action: string;
  target: string;
  status: string;
}

const AuditLogs = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRole, setFilterRole] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/admin/audit-logs');
      const data = await response.json();
      setLogs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const filteredLogs = logs.filter(log => {
    const matchesSearch = searchTerm === '' || 
      log.user?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.target?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = filterRole === 'all' || log.role === filterRole;
    const matchesStatus = filterStatus === 'all' || log.status === filterStatus;
    return matchesSearch && matchesRole && matchesStatus;
  });

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>Audit Logs</h1>
        <p>Track all system actions and changes</p>
      </div>

      <div className="admin-controls">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search logs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="filters">
          <select value={filterRole} onChange={(e) => setFilterRole(e.target.value)}>
            <option value="all">All Roles</option>
            <option value="Executive">Executive</option>
            <option value="Officer">Officer</option>
            <option value="Citizen">Citizen</option>
          </select>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
            <option value="all">All Status</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      <div className="table-container">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>User</th>
              <th>Role</th>
              <th>Action</th>
              <th>Target</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="loading">Loading...</td></tr>
            ) : error ? (
              <tr><td colSpan={6} className="error-state"><p>{error}</p><button className="retry-btn" onClick={fetchLogs}>Retry</button></td></tr>
            ) : filteredLogs.length === 0 ? (
              <tr><td colSpan={6} className="empty">No audit logs found</td></tr>
            ) : (
              filteredLogs.map(log => (
                <tr key={log.id}>
                  <td>{log.timestamp?.split('T')[1]?.split('.')[0] || log.timestamp?.split('T')[0]}</td>
                  <td>{log.user || '-'}</td>
                  <td><span className={`role ${log.role?.toLowerCase()}`}>{log.role}</span></td>
                  <td>{log.action}</td>
                  <td>{log.target || '-'}</td>
                  <td><span className={`status ${log.status}`}>{log.status}</span></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AuditLogs;