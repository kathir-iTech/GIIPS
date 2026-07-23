import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { Building, AlertCircle, CheckCircle, Clock, Users, TrendingUp, Star, ChevronUp, ChevronDown } from 'lucide-react';
import { getDeptI18nKey } from '../data/departments';
import './Admin.css';

interface DepartmentData {
  department: string;
  open_incidents: number;
  critical_incidents: number;
  assigned_officers: number;
  avg_resolution_time: number;
  completion_percentage: number;
  workload_indicator: number;
  avg_citizen_rating?: number | null;
  rating_count?: number;
  aging_count: number;
}

type SortKey = keyof Pick<DepartmentData, 'department' | 'open_incidents' | 'avg_resolution_time' | 'avg_citizen_rating' | 'aging_count'>;

const DepartmentManagement = () => {
  const { t } = useTranslation();
  const [departments, setDepartments] = useState<DepartmentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('open_incidents');
  const [sortAsc, setSortAsc] = useState(false);

  useEffect(() => {
    fetchDepartments();
  }, []);

  const fetchDepartments = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/admin/departments');
      const data = await response.json();
      setDepartments(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('departmentManagement.loadError'));
    } finally {
      setLoading(false);
    }
  };

  const getWorkloadColor = (value: number) => {
    if (value > 0.8) return 'high';
    if (value > 0.5) return 'medium';
    return 'low';
  };

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(p => !p);
    else { setSortKey(key); setSortAsc(key === 'department'); }
  };

  const sortedDepts = [...departments].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    if (aVal == null && bVal == null) return 0;
    if (aVal == null) return 1;
    if (bVal == null) return -1;
    if (typeof aVal === 'string' && typeof bVal === 'string') return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    return sortAsc ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
  });

  const sortIcon = (key: SortKey) => {
    if (sortKey !== key) return null;
    return sortAsc ? <ChevronUp size={14} /> : <ChevronDown size={14} />;
  };

  return (
    <div className="admin-page">
      <div className="admin-header">
<h1>{t('departmentManagement.header.title')}</h1>
<p>{t('departmentManagement.header.subtitle')}</p>
      </div>

      <div className="dept-grid">
        {loading ? (
          <div className="loading">{t('departmentManagement.loading')}</div>
        ) : error ? (
          <div className="error-state">
            <p>{error}</p>
            <button className="retry-btn" onClick={fetchDepartments}>{t('departmentManagement.retry')}</button>
          </div>
        ) : departments.length === 0 ? (
          <div className="empty">{t('departmentManagement.empty')}</div>
        ) : (
          departments.map(dept => (
            <div className="dept-card" key={dept.department}>
              <div className="dept-header">
                <Building size={24} />
                <h3>{t(getDeptI18nKey(dept.department))}</h3>
              </div>
              <div className="dept-stats">
                <div className="stat">
                  <span className="value">{dept.open_incidents}</span>
                  <span className="label">{t('departmentManagement.openIncidents')}</span>
                </div>
                <div className="stat">
                  <span className="value">{dept.critical_incidents}</span>
                  <span className="label">{t('departmentManagement.critical')}</span>
                </div>
                <div className="stat">
                  <span className="value">{dept.assigned_officers}</span>
                  <span className="label">{t('departmentManagement.officers')}</span>
                </div>
                <div className="stat">
                  <span className="value">{(dept.avg_resolution_time ?? 0).toFixed(1)}d</span>
                  <span className="label">{t('departmentManagement.avgResolution')}</span>
                </div>
                <div className="stat">
                  <span className="value">{((dept.completion_percentage ?? 0) * 100).toFixed(0)}%</span>
                  <span className="label">{t('departmentManagement.completion')}</span>
                </div>
                <div className={`workload ${getWorkloadColor(dept.workload_indicator)}`}>
                  {t('departmentManagement.workload')}: {((dept.workload_indicator ?? 0) * 100).toFixed(0)}%
                </div>
                <div className="stat">
                  <span className="value rating-value">
                    {dept.avg_citizen_rating != null ? (
                      <><Star size={14} className="star-filled" /> {dept.avg_citizen_rating.toFixed(1)} <span className="rating-count">({dept.rating_count})</span></>
                    ) : (
                      '—'
                    )}
                  </span>
                  <span className="label">{t('departmentManagement.citizenRating')}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="comparison-section">
        <h2 className="comparison-title">Department Comparison</h2>
        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('department')} className={sortKey === 'department' ? 'active' : ''}>
                  Department {sortIcon('department')}
                </th>
                <th onClick={() => handleSort('open_incidents')} className={sortKey === 'open_incidents' ? 'active' : ''}>
                  Open Incidents {sortIcon('open_incidents')}
                </th>
                <th onClick={() => handleSort('avg_resolution_time')} className={sortKey === 'avg_resolution_time' ? 'active' : ''}>
                  Avg Resolution {sortIcon('avg_resolution_time')}
                </th>
                <th onClick={() => handleSort('avg_citizen_rating')} className={sortKey === 'avg_citizen_rating' ? 'active' : ''}>
                  Avg Rating {sortIcon('avg_citizen_rating')}
                </th>
                <th onClick={() => handleSort('aging_count')} className={sortKey === 'aging_count' ? 'active' : ''}>
                  Aging (&gt;30d) {sortIcon('aging_count')}
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedDepts.map(dept => (
                <tr key={dept.department}>
                  <td className="dept-name">{t(getDeptI18nKey(dept.department))}</td>
                  <td>{dept.open_incidents}</td>
                  <td>{(dept.avg_resolution_time ?? 0).toFixed(1)}d</td>
                  <td>{dept.avg_citizen_rating != null ? dept.avg_citizen_rating.toFixed(1) : '—'}</td>
                  <td className={dept.aging_count > 0 ? 'aging-warn' : ''}>{dept.aging_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DepartmentManagement;