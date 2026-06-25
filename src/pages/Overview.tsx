import { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import type { DashboardData } from '../types';
import KPICard from '../components/KPICard';
import Header from '../components/Header';
import './Overview.css';

const Overview = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getDashboardData().then(setData).catch(err => setError(err.message)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading dashboard data...</div>;
  if (error) return <div className="page-error">Error: {error}</div>;
  if (!data) return null;

  return (
    <div className="overview-page">
      <Header title="Dashboard Overview" subtitle="Municipal grievance intelligence summary" />
      <div className="page-content">
        <section className="before-after-section">
          <div className="before-after-card">
            <div className="before-after-header">
              <h2>Workload Transformation</h2>
              <span className="insight-badge">Key Insight</span>
            </div>
            <p className="before-after-quote">"100 complaints may represent only 5 real incidents."</p>
            <div className="before-after-comparison">
              <div className="comparison-item before">
                <span className="comparison-label">Before</span>
                <span className="comparison-value">{data.beforeAfter.before.toLocaleString()}</span>
                <span className="comparison-unit">Complaints</span>
              </div>
              <div className="comparison-arrow">
                <svg width="48" height="24" viewBox="0 0 48 24"><path d="M0 12H40M40 12L32 4M40 12L32 20" stroke="#16a34a" strokeWidth="2" strokeLinecap="round"/></svg>
                <span className="reduction-badge">{data.beforeAfter.reduction}% reduction</span>
              </div>
              <div className="comparison-item after">
                <span className="comparison-label">After</span>
                <span className="comparison-value">{data.beforeAfter.after.toLocaleString()}</span>
                <span className="comparison-unit">Incidents</span>
              </div>
            </div>
          </div>
        </section>

        <section className="kpi-section">
          <div className="kpi-grid">
            <KPICard title="Total Complaints" value={data.totalComplaints.toLocaleString()} subtitle="Citizen submissions received" />
            <KPICard title="Unique Incidents" value={data.uniqueIncidents.toLocaleString()} subtitle="Actionable items identified" variant="success" />
            <KPICard title="Workload Reduction" value={`${data.workloadReduction}%`} subtitle="Administrative efficiency gain" variant="success" />
            <KPICard title="Critical Incidents" value={data.criticalIncidents} subtitle="Require immediate attention" variant="critical" />
            <KPICard title="High Priority" value={data.highPriorityIncidents} subtitle="Scheduled for urgent action" />
            <KPICard title="Avg. Resolution Score" value={data.avgResolutionScore} subtitle="Priority-based scoring" />
          </div>
        </section>

        <section className="charts-section">
          <div className="chart-row">
            <div className="chart-card">
              <h3>Incident Trend (Monthly)</h3>
              <Plot data={[{ x: data.trendData.map(d => d.date), y: data.trendData.map(d => d.incidents), type: 'scatter', mode: 'lines+markers', line: { color: '#1e293b', width: 2 } }]}
                layout={{ paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', margin: { t: 20, r: 20, b: 40, l: 40 }, xaxis: { showgrid: false }, yaxis: { showgrid: true, gridcolor: '#f1f5f9' }, height: 280 }}
                config={{ displayModeBar: false, responsive: true }} style={{ width: '100%' }} />
            </div>
            <div className="executive-summary-card">
              <h3>Executive Summary</h3>
              <div className="summary-content">
                <div className="summary-item">
                  <span className="summary-label">Processing Efficiency</span>
                  <div className="efficiency-bar"><div className="efficiency-fill" style={{ width: `${data.workloadReduction}%` }}></div></div>
                  <span className="efficiency-value">{data.workloadReduction}%</span>
                </div>
                <div className="summary-stat"><span className="stat-value">{data.totalComplaints.toLocaleString()}</span><span className="stat-label">complaints processed</span></div>
                <div className="summary-stat"><span className="stat-value">{data.uniqueIncidents}</span><span className="stat-label">unique incidents identified</span></div>
                <div className="summary-stat"><span className="stat-value">{data.criticalIncidents}</span><span className="stat-label">critical incidents</span></div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Overview;
