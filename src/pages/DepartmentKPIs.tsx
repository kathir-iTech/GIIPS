import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import Header from '../components/Header';
import { getDeptI18nKey, getDeptIconKeyword } from '../data/departments';
import { AlertCircle, Users, Clock, CheckCircle, Star, Shield, Activity, Building2 } from 'lucide-react';
import './ExecutiveDashboard.css';

const DepartmentKPIs = () => {
  const { t } = useTranslation();
  const [departments, setDepartments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.get('/admin/departments').then(r => r.json()),
      api.getOfficerPerformance(),
    ]).then(([depts, perf]) => {
      if (cancelled) return;
      const officerCount: Record<string, number> = {};
      (perf || []).forEach((o: any) => {
        const d = o.department || 'Unknown';
        officerCount[d] = (officerCount[d] || 0) + 1;
      });
      const merged = (depts || []).map((d: any) => ({
        ...d,
        officer_count: officerCount[d.department] || 0,
      }));
      setDepartments(merged);
    }).catch(err => {
      if (!cancelled) setError(err.message);
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="page-loading"><div className="spinner" /><span>{t('departmentKPIs.loading')}</span></div>;
  if (error) return <div className="page-error"><AlertCircle size={20} /> {error}</div>;

  return (
    <div className="exec-dashboard">
      <Header title={t('departmentKPIs.title')} subtitle={t('departmentKPIs.subtitle')} />
      <div style={{ padding: '0 32px 32px', display: 'flex', flexDirection: 'column', gap: 24 }}>
        {departments.length === 0 ? (
          <div className="empty-chart" style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>{t('departmentKPIs.empty')}</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 20 }}>
            {departments.map((dept: any, idx: number) => {
              const slaPct = dept.completion_percentage ?? 0;
              const avgResDays = dept.avg_resolution_time ?? 0;
              const avgRating = dept.avg_citizen_rating;
              const openCount = dept.open_incidents ?? 0;
              const officerCount = dept.officer_count ?? dept.assigned_officers ?? 0;
              return (
                <div key={idx} className="section-card glass-card" style={{ padding: 20, borderTop: `3px solid hsl(${idx * 45}, 60%, 50%)` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <Building2 size={20} style={{ color: `hsl(${idx * 45}, 60%, 50%)` }} />
                    <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>{t(getDeptI18nKey(dept.department))}</h3>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <div className="dept-stat"><Activity size={14} /><span className="dept-stat-label">{t('departmentKPIs.resolutionRate')}</span><span className="dept-stat-value">{slaPct}%</span></div>
                    <div className="dept-stat"><Clock size={14} /><span className="dept-stat-label">{t('departmentKPIs.avgResolution')}</span><span className="dept-stat-value">{avgResDays}d</span></div>
                    <div className="dept-stat"><CheckCircle size={14} /><span className="dept-stat-label">{t('departmentKPIs.slaCompliance')}</span><span className="dept-stat-value">{slaPct}%</span></div>
                    <div className="dept-stat"><Star size={14} /><span className="dept-stat-label">{t('departmentKPIs.avgRating')}</span><span className="dept-stat-value">{avgRating != null ? `${avgRating}/5` : '—'}</span></div>
                    <div className="dept-stat"><Users size={14} /><span className="dept-stat-label">{t('departmentKPIs.officers')}</span><span className="dept-stat-value">{officerCount}</span></div>
                    <div className="dept-stat"><Shield size={14} /><span className="dept-stat-label">{t('departmentKPIs.openIncidents')}</span><span className="dept-stat-value">{openCount}</span></div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default DepartmentKPIs;
