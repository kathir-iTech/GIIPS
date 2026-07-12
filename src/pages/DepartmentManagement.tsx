import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { Building, AlertCircle, CheckCircle, Clock, Users, TrendingUp } from 'lucide-react';
import './Admin.css';

interface DepartmentData {
  department: string;
  open_incidents: number;
  critical_incidents: number;
  assigned_officers: number;
  avg_resolution_time: number;
  completion_percentage: number;
  workload_indicator: number;
}

const DepartmentManagement = () => {
  const { t } = useTranslation();
  const [departments, setDepartments] = useState<DepartmentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
                <h3>{dept.department}</h3>
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
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default DepartmentManagement;