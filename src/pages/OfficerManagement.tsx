import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { UserPlus, Search, Lock, Unlock } from 'lucide-react';
import { DEPARTMENTS } from '../data/departments';
import './Admin.css';

interface Officer {
  id: string;
  full_name: string;
  email: string;
  district: string;
  created_at: string;
  status: string;
}

const OfficerManagement = () => {
  const { t } = useTranslation();
  const [officers, setOfficers] = useState<Officer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const [formData, setFormData] = useState({ full_name: '', email: '', password: '', district: '', department: '' });

  useEffect(() => {
    fetchOfficers();
  }, []);

  const fetchOfficers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/admin/officers');
      const data = await response.json();
      setOfficers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('officerManagement.loadError'));
    } finally {
      setLoading(false);
    }
  };

  const filteredOfficers = officers.filter(o => 
    o.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    o.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    o.district.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleDisable = async (id: string) => {
    try {
      setError(null);
      await api.patch(`/admin/officers/${id}/disable`, {});
      fetchOfficers();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('officerManagement.disableError'));
    }
  };

  const handleEnable = async (id: string) => {
    try {
      setError(null);
      await api.patch(`/admin/officers/${id}/enable`, {});
      fetchOfficers();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('officerManagement.enableError'));
    }
  };

  const handleCreateOfficer = async () => {
    if (!formData.email.endsWith('@gov.in')) {
      setDialogError(t('officerManagement.govEmailError'));
      return;
    }
    try {
      setDialogError(null);
      await api.post('/admin/officers', formData);
      setShowAddDialog(false);
      fetchOfficers();
    } catch (err) {
      setDialogError(err instanceof Error ? err.message : t('officerManagement.createError'));
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-header">
<h1>{t('officerManagement.header.title')}</h1>
<p>{t('officerManagement.header.subtitle')}</p>
      </div>

      <div className="admin-controls">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder={t('officerManagement.searchPlaceholder')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <button className="btn-primary" onClick={() => setShowAddDialog(true)}>
          <UserPlus size={16} /> {t('officerManagement.addOfficer')}
        </button>
      </div>

      <div className="stats-cards">
        <div className="stat-card">
<h3>{officers.length}</h3>
<p>{t('officerManagement.totalOfficers')}</p>
        </div>
        <div className="stat-card">
<h3>{officers.filter(o => o.status === 'active').length}</h3>
<p>{t('officerManagement.activeOfficers')}</p>
        </div>
        <div className="stat-card">
<h3>{officers.filter(o => o.status === 'disabled').length}</h3>
<p>{t('officerManagement.disabledOfficers')}</p>
        </div>
      </div>

      <div className="table-container">
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t('officerManagement.colOfficerId')}</th>
              <th>{t('officerManagement.colName')}</th>
              <th>{t('officerManagement.colEmail')}</th>
              <th>{t('officerManagement.colDistrict')}</th>
              <th>{t('officerManagement.colStatus')}</th>
              <th>{t('officerManagement.colCreated')}</th>
              <th>{t('officerManagement.colActions')}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="loading">{t('officerManagement.loading')}</td></tr>
            ) : error ? (
              <tr><td colSpan={7} className="error-state"><p>{error}</p><button className="retry-btn" onClick={fetchOfficers}>{t('officerManagement.retry')}</button></td></tr>
            ) : filteredOfficers.length === 0 ? (
              <tr><td colSpan={7} className="empty">{t('officerManagement.empty')}</td></tr>
            ) : (
              filteredOfficers.map(officer => (
                <tr key={officer.id}>
                  <td>{officer.id}</td>
                  <td>{officer.full_name}</td>
                  <td>{officer.email}</td>
                  <td>{officer.district}</td>
                  <td><span className={`status ${officer.status}`}>{officer.status}</span></td>
                  <td>{officer.created_at?.split('T')[0]}</td>
                  <td>
                    <div className="actions">
                      {officer.status === 'active' ? 
                        <button onClick={() => handleDisable(officer.id)}><Lock size={16} /></button> :
                        <button onClick={() => handleEnable(officer.id)}><Unlock size={16} /></button>
                      }
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showAddDialog && (
        <div className="dialog-overlay">
          <div className="dialog">
            <h3>{t('officerManagement.dialogTitle')}</h3>
            <div className="form-grid">
              <input placeholder={t('officerManagement.fieldFullName')} value={formData.full_name} onChange={e => setFormData({...formData, full_name: e.target.value})} />
              <input placeholder={t('officerManagement.fieldEmail')} value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} />
              <input placeholder={t('officerManagement.fieldDistrict')} value={formData.district} onChange={e => setFormData({...formData, district: e.target.value})} />
              <select value={formData.department} onChange={e => setFormData({...formData, department: e.target.value})}>
                <option value="">{t('officerManagement.fieldDepartment')}</option>
                {DEPARTMENTS.map(d => (
                  <option key={d.slug} value={d.nameEn}>{d.nameEn}</option>
                ))}
              </select>
              <input type="password" placeholder={t('officerManagement.fieldPassword')} value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} />
            </div>
            {dialogError && <div className="error-state"><p>{dialogError}</p></div>}
            <div className="dialog-actions">
              <button onClick={() => setShowAddDialog(false)}>{t('officerManagement.cancel')}</button>
              <button className="btn-primary" onClick={handleCreateOfficer}>{t('officerManagement.create')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OfficerManagement;