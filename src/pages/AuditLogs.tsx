import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation();
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
      setError(err instanceof Error ? err.message : t('auditLogs.loadError'));
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
        <h1>{t('auditLogs.header.title')}</h1>
        <p>{t('auditLogs.header.subtitle')}</p>
      </div>

      <div className="admin-controls">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder={t('auditLogs.searchPlaceholder')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="filters">
          <select value={filterRole} onChange={(e) => setFilterRole(e.target.value)}>
            <option value="all">{t('auditLogs.allRoles')}</option>
            <option value="Executive">{t('nav.roleExecutive')}</option>
            <option value="Officer">{t('nav.roleOfficer')}</option>
            <option value="Citizen">{t('nav.roleCitizen')}</option>
          </select>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
            <option value="all">{t('auditLogs.allStatus')}</option>
            <option value="success">{t('auditLogs.success')}</option>
            <option value="failed">{t('auditLogs.failed')}</option>
          </select>
        </div>
      </div>

      <div className="table-container">
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t('auditLogs.colTimestamp')}</th>
              <th>{t('auditLogs.colUser')}</th>
              <th>{t('auditLogs.colRole')}</th>
              <th>{t('auditLogs.colAction')}</th>
              <th>{t('auditLogs.colTarget')}</th>
              <th>{t('auditLogs.colStatus')}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="loading">{t('auditLogs.loading')}</td></tr>
            ) : error ? (
              <tr><td colSpan={6} className="error-state"><p>{error}</p><button className="retry-btn" onClick={fetchLogs}>{t('auditLogs.retry')}</button></td></tr>
            ) : filteredLogs.length === 0 ? (
              <tr><td colSpan={6} className="empty">{t('auditLogs.empty')}</td></tr>
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