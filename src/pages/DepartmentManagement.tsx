import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { Building, AlertCircle, CheckCircle, Clock, Users, TrendingUp, Star, ChevronUp, ChevronDown, Layers } from 'lucide-react';
import { getDeptI18nKey } from '../data/departments';
import { getDepartmentHead } from '../data/officerDirectory';
import { Phone, User as UserIcon } from 'lucide-react';
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
  const [trendOfficer, setTrendOfficer] = useState<string | null>(null);
  const [trendData, setTrendData] = useState<any[]>([]);
  const [trendLoading, setTrendLoading] = useState(false);

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

  const openOfficerTrend = async (name: string) => {
    setTrendOfficer(name);
    setTrendData([]);
    setTrendLoading(true);
    try {
      const data = await api.getOfficerPerformanceTrend(name);
      if (Array.isArray(data)) setTrendData(data);
    } catch {
      setTrendData([]);
    } finally {
      setTrendLoading(false);
    }
  };

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
              {(() => {
                const head = getDepartmentHead(dept.department);
                if (!head) return null;
                return (
                  <div className="dept-contact-card">
                    <div className="dept-contact-row">
                      <UserIcon size={13} />
                      <span>{head.name}</span>
                    </div>
                    <div className="dept-contact-row">
                      <Phone size={13} />
                      <a href={`tel:${head.phone}`} className="dept-contact-phone">{head.phone}</a>
                    </div>
                  </div>
                );
              })()}
            </div>
          ))
        )}
      </div>

      <div className="comparison-section">
        <h2 className="comparison-title">{t('departmentManagement.comparisonTitle')}</h2>
        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('department')} className={sortKey === 'department' ? 'active' : ''}>
                  {t('departmentManagement.columnDepartment')} {sortIcon('department')}
                </th>
                <th onClick={() => handleSort('open_incidents')} className={sortKey === 'open_incidents' ? 'active' : ''}>
                  {t('departmentManagement.columnOpenIncidents')} {sortIcon('open_incidents')}
                </th>
                <th onClick={() => handleSort('avg_resolution_time')} className={sortKey === 'avg_resolution_time' ? 'active' : ''}>
                  {t('departmentManagement.columnAvgResolution')} {sortIcon('avg_resolution_time')}
                </th>
                <th>{t('departmentManagement.benchmarkTitle')}</th>
                <th onClick={() => handleSort('avg_citizen_rating')} className={sortKey === 'avg_citizen_rating' ? 'active' : ''}>
                  {t('departmentManagement.columnAvgRating')} {sortIcon('avg_citizen_rating')}
                </th>
                <th onClick={() => handleSort('aging_count')} className={sortKey === 'aging_count' ? 'active' : ''}>
                  {t('departmentManagement.columnAging')} {sortIcon('aging_count')}
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedDepts.map(dept => (
                <tr key={dept.department}>
                  <td className="dept-name">{t(getDeptI18nKey(dept.department))}</td>
                  <td>{dept.open_incidents}</td>
                  <td>{(dept.avg_resolution_time ?? 0).toFixed(1)}d</td>
                  <td>{(() => {
                    const diff = (dept.avg_resolution_time ?? 0) - avgAll;
                    const label = Math.abs(diff) < 0.05 ? t('departmentManagement.benchmarkSame') : diff < 0 ? t('departmentManagement.benchmarkFaster') : t('departmentManagement.benchmarkSlower');
                    return <span className={`benchmark-badge ${diff <= 0 ? 'benchmark-good' : 'benchmark-bad'}`}>{label}</span>;
                  })()}</td>
                  <td>{dept.avg_citizen_rating != null ? dept.avg_citizen_rating.toFixed(1) : '—'}</td>
                  <td className={dept.aging_count > 0 ? 'aging-warn' : ''}>{dept.aging_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="comparison-section">
        <h2 className="comparison-title">{t('departmentManagement.officerLeaderboard')}</h2>
        {perfLoading ? (
          <div className="loading">{t('departmentManagement.loading')}</div>
        ) : officerPerf.length === 0 ? (
          <div className="empty">{t('departmentManagement.emptyPerf')}</div>
        ) : (
          <div className="comparison-table-wrapper">
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>{t('departmentManagement.columnRank')}</th>
                  <th>{t('departmentManagement.columnOfficerName')}</th>
                  <th>{t('departmentManagement.columnDept')}</th>
                  <th>{t('departmentManagement.columnSkills')}</th>
                  <th>{t('departmentManagement.columnAvgDays')}</th>
                  <th>{t('departmentManagement.columnTotalResolved')}</th>
                  <th>{t('departmentManagement.columnEscalationRate')}</th>
                  <th>{t('departmentManagement.columnAvgQuality')}</th>
                </tr>
              </thead>
              <tbody>
                {officerPerf.map((o, i) => (
                  <tr key={o.officer_name}>
                    <td className="rank-cell">{i + 1}</td>
                    <td className="dept-name" style={{ cursor: 'pointer', color: '#818cf8' }} onClick={() => openOfficerTrend(o.officer_name)}>{o.officer_name}</td>
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
          <h2 className="comparison-title">{t('departmentManagement.histogramTitle')}</h2>
          <Plot
            data={[{x: histogram.map(h=>h.range), y: histogram.map(h=>h.count), type:'bar', marker:{color:'#3b82f6'}}]}
            layout={{title:'', width: null, height: 250, autosize:true, paper_bgcolor:'transparent', plot_bgcolor:'transparent', font:{color:'var(--text-primary)'}, margin:{t:10,b:30,l:40,r:10}}}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%' }}
          />
        </div>
      )}

      <div className="comparison-section">
        <h2 className="comparison-title">{t('departmentManagement.slaReport')}</h2>
        {slaLoading ? <div className="loading">{t('departmentManagement.loading')}</div> : (
          <div className="comparison-table-wrapper">
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>{t('departmentManagement.slaColumnDept')}</th><th>{t('departmentManagement.slaColumnOpen')}</th><th>{t('departmentManagement.slaColumnWithin')}</th><th>{t('departmentManagement.slaColumnBreached')}</th><th>{t('departmentManagement.slaColumnAvgBreach')}</th>
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

      <div className="comparison-section">
        <a href="/executive/escalation-matrix" className="action-btn" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', textDecoration: 'none', marginBottom: '1.5rem' }}>
          <Layers size={14} /> {t('department.escalationMatrix')}
        </a>
      </div>

      <div className="heatmap-section">
        <h2 className="comparison-title">{t('departmentManagement.heatmapTitle')}</h2>
        <div className="heatmap-controls">
          <select value={selectedDept} onChange={e => setSelectedDept(e.target.value)}>
            <option value="">{t('departmentManagement.heatmapAllDepts')}</option>
            {heatmapDepts.map(d => <option key={d} value={d}>{t(getDeptI18nKey(d))}</option>)}
          </select>
        </div>
        {heatmap && (
          <div className="heatmap-grid" style={{display:'grid', gridTemplateColumns: '80px repeat(24, 1fr)', gap: '2px', overflowX: 'auto'}}>
            <div></div>
            {heatmap.hours.map((h: number) => <div key={h} className="heatmap-header" style={{fontSize:'0.65rem',textAlign:'center'}}>{h}{t('common.time.hourSuffix')}</div>)}
            {heatmap.data.map((row: number[], di: number) => (
              <React.Fragment key={di}>
                <div className="heatmap-day" style={{fontSize:'0.75rem',display:'flex',alignItems:'center'}}>{heatmap.days[di]}</div>
                {row.map((v: number, hi: number) => {
                  const max = Math.max(...heatmap.data.flat(), 1);
                  const opacity = 0.1 + (v / max) * 0.9;
                  return <div key={hi} className="heatmap-cell" style={{background:`rgba(59,130,246,${opacity})`, height:'24px', borderRadius:'2px', position:'relative'}} title={t('departmentManagement.heatmapCellTitle', { day: heatmap.days[di], hour: hi, count: v })} />;
                })}
              </React.Fragment>
            ))}
          </div>
        )}
      </div>

      {trendOfficer && (
        <div className="dialog-overlay" onClick={() => setTrendOfficer(null)}>
          <div className="dialog" onClick={e => e.stopPropagation()} style={{ minWidth: 560 }}>
            <h3>{t('departmentManagement.officerTrendTitle')}</h3>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '0 0 16px' }}>
              {t('departmentManagement.officerTrendSubtitle', { name: trendOfficer })}
            </p>
            {trendLoading ? (
              <div className="loading">{t('departmentManagement.loading')}</div>
            ) : trendData.length === 0 ? (
              <div className="empty">{t('departmentManagement.officerTrendEmpty')}</div>
            ) : (
              <Plot
                data={[
                  {
                    x: trendData.map((d: any) => d.week),
                    y: trendData.map((d: any) => d.avg_days_to_resolve ?? 0),
                    type: 'scatter', mode: 'lines+markers',
                    name: t('departmentManagement.officerTrendAvgDays'),
                    line: { color: '#3b82f6', width: 2 },
                    marker: { size: 6 },
                  },
                  {
                    x: trendData.map((d: any) => d.week),
                    y: trendData.map((d: any) => d.total_resolved ?? 0),
                    type: 'bar',
                    name: t('departmentManagement.officerTrendResolved'),
                    marker: { color: 'rgba(139,92,246,0.35)' },
                    yaxis: 'y2',
                  },
                ]}
                layout={{
                  title: '', height: 280, autosize: true,
                  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
                  font: { color: 'var(--text-primary)' },
                  margin: { t: 10, b: 40, l: 40, r: 40 },
                  legend: { orientation: 'h', y: -0.2 },
                  yaxis: { gridcolor: 'rgba(255,255,255,0.05)', title: '' },
                  yaxis2: { overlaying: 'y', side: 'right', showgrid: false, title: '' },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            )}
            <div className="dialog-actions">
              <button onClick={() => setTrendOfficer(null)}>{t('departmentManagement.officerTrendClose')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DepartmentManagement;