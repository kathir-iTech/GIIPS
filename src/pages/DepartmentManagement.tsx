import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { Building, AlertCircle, CheckCircle, Clock, Users, TrendingUp, Star, ChevronUp, ChevronDown } from 'lucide-react';
import { getDeptI18nKey } from '../data/departments';
import Plot from 'react-plotly.js';
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

interface OfficerPerf {
  officer_name: string;
  department: string;
  avg_days_to_resolve: number;
  total_resolved: number;
  escalation_count?: number;
  esc_rate?: number;
  skills?: string;
  avg_quality_score?: number;
}

type SortKey = keyof Pick<DepartmentData, 'department' | 'open_incidents' | 'avg_resolution_time' | 'avg_citizen_rating' | 'aging_count'>;

const DepartmentManagement = () => {
  const { t } = useTranslation();
  const [departments, setDepartments] = useState<DepartmentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('open_incidents');
  const [sortAsc, setSortAsc] = useState(false);
  const [officerPerf, setOfficerPerf] = useState<OfficerPerf[]>([]);
  const [perfLoading, setPerfLoading] = useState(false);
  const [slaReport, setSlaReport] = useState<any[]>([]);
  const [slaLoading, setSlaLoading] = useState(false);
  const [heatmap, setHeatmap] = useState<any>(null);
  const [selectedDept, setSelectedDept] = useState('');
  const [heatmapDepts, setHeatmapDepts] = useState<string[]>([]);
  const [histogram, setHistogram] = useState<any[]>([]);

  useEffect(() => {
    fetchDepartments();
    fetchOfficerPerformance();
    fetchSlaReport();
    api.get('/admin/departments/list').then(r => r.json()).then((data: any[]) => setHeatmapDepts(data.map((d: any) => d.slug))).catch(() => {});
  }, []);

  useEffect(() => {
    api.get(`/admin/department-heatmap?department=${encodeURIComponent(selectedDept)}`).then(r => r.json()).then(setHeatmap).catch(() => {});
  }, [selectedDept]);

  const fetchSlaReport = async () => {
    setSlaLoading(true);
    try { setSlaReport(await api.getDepartmentSlaReport()); } catch {}
    setSlaLoading(false);
  };

  const fetchHistogram = async () => {
    try {
      const res = await api.get('/admin/resolution-histogram');
      const data = await res.json();
      setHistogram(data);
    } catch {}
  };

  const fetchOfficerPerformance = async () => {
    setPerfLoading(true);
    try {
      const data = await api.getOfficerPerformance();
      setOfficerPerf(data);
    } catch {
      // non-critical
    } finally {
      setPerfLoading(false);
    }
  };

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

  const avgAll = departments.reduce((s, d) => s + d.avg_resolution_time, 0) / departments.length;

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
                  <td>{(dept.avg_resolution_time ?? 0).toFixed(1)}d
                    <span className={`benchmark-badge ${dept.avg_resolution_time <= avgAll ? 'benchmark-good' : 'benchmark-bad'}`}>
                      {dept.avg_resolution_time <= avgAll ? '-' : '+'}{(Math.abs(dept.avg_resolution_time - avgAll)).toFixed(1)}
                    </span>
                  </td>
                  <td>{dept.avg_citizen_rating != null ? dept.avg_citizen_rating.toFixed(1) : '—'}</td>
                  <td className={dept.aging_count > 0 ? 'aging-warn' : ''}>{dept.aging_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="comparison-section">
        <h2 className="comparison-title">Officer Response Time Leaderboard</h2>
        {perfLoading ? (
          <div className="loading">Loading...</div>
        ) : officerPerf.length === 0 ? (
          <div className="empty">No resolved incidents with officer assignments yet.</div>
        ) : (
          <div className="comparison-table-wrapper">
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Officer Name</th>
                  <th>Department</th>
                  <th>Skills</th>
                  <th>Avg Days to Resolve</th>
                  <th>Total Resolved</th>
                  <th>Escalation Rate</th>
                  <th>Avg Quality</th>
                </tr>
              </thead>
              <tbody>
                {officerPerf.map((o, i) => (
                  <tr key={o.officer_name}>
                    <td className="rank-cell">{i + 1}</td>
                    <td className="dept-name">{o.officer_name}</td>
                    <td>{t(getDeptI18nKey(o.department))}</td>
                    <td>{(o.skills ? JSON.parse(o.skills) : []).map((s: string) => <span key={s} className="skill-badge">{s}</span>)}</td>
                    <td className={o.avg_days_to_resolve <= 7 ? 'perf-good' : o.avg_days_to_resolve <= 14 ? 'perf-ok' : 'perf-slow'}>
                      {o.avg_days_to_resolve.toFixed(1)}d
                    </td>
                    <td>{o.total_resolved}</td>
                    <td>{o.esc_rate != null ? `${o.esc_rate.toFixed(0)}%` : '—'}</td>
                    <td>{o.avg_quality_score != null ? `${o.avg_quality_score.toFixed(0)}/100` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {histogram.length > 0 && (
        <div className="histogram-section">
          <h2 className="comparison-title">Resolution Time Distribution</h2>
          <Plot
            data={[{x: histogram.map(h=>h.range), y: histogram.map(h=>h.count), type:'bar', marker:{color:'#3b82f6'}}]}
            layout={{title:'', width: null, height: 250, autosize:true, paper_bgcolor:'transparent', plot_bgcolor:'transparent', font:{color:'var(--text-primary)'}, margin:{t:10,b:30,l:40,r:10}}}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%' }}
          />
        </div>
      )}

      <div className="comparison-section">
        <h2 className="comparison-title">Department SLA Report</h2>
        {slaLoading ? <div className="loading">Loading...</div> : (
          <div className="comparison-table-wrapper">
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>Department</th><th>Open</th><th>Within SLA</th><th>Breached SLA</th><th>Avg Breach (days)</th>
                </tr>
              </thead>
              <tbody>
                {slaReport.map((s: any) => (
                  <tr key={s.department}>
                    <td className="dept-name">{t(getDeptI18nKey(s.department))}</td>
                    <td>{s.total_open}</td>
                    <td className="sla-green-text">{s.within_sla}</td>
                    <td className={s.breached_sla > 0 ? 'sla-red-text' : ''}>{s.breached_sla}</td>
                    <td>{s.avg_breach_duration_days ? s.avg_breach_duration_days.toFixed(1) + 'd' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="heatmap-section">
        <h2 className="comparison-title">Complaint Arrival Heatmap</h2>
        <div className="heatmap-controls">
          <select value={selectedDept} onChange={e => setSelectedDept(e.target.value)}>
            <option value="">All Departments</option>
            {heatmapDepts.map(d => <option key={d} value={d}>{t(getDeptI18nKey(d))}</option>)}
          </select>
        </div>
        {heatmap && (
          <div className="heatmap-grid" style={{display:'grid', gridTemplateColumns: '80px repeat(24, 1fr)', gap: '2px', overflowX: 'auto'}}>
            <div></div>
            {heatmap.hours.map((h: number) => <div key={h} className="heatmap-header" style={{fontSize:'0.65rem',textAlign:'center'}}>{h}h</div>)}
            {heatmap.data.map((row: number[], di: number) => (
              <React.Fragment key={di}>
                <div className="heatmap-day" style={{fontSize:'0.75rem',display:'flex',alignItems:'center'}}>{heatmap.days[di]}</div>
                {row.map((v: number, hi: number) => {
                  const max = Math.max(...heatmap.data.flat(), 1);
                  const opacity = 0.1 + (v / max) * 0.9;
                  return <div key={hi} className="heatmap-cell" style={{background:`rgba(59,130,246,${opacity})`, height:'24px', borderRadius:'2px', position:'relative'}} title={`${heatmap.days[di]} ${hi}:00 — ${v} complaints`} />;
                })}
              </React.Fragment>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DepartmentManagement;