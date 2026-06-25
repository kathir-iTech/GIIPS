import { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import type { DashboardData } from '../types';
import Header from '../components/Header';
import './Overview.css';

const Overview = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getDashboardData().then(setData).catch(err => setError(err.message)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>Loading dashboard...</span></div>;
  if (error) return <div className="page-error">Error: {error}</div>;
  if (!data) return null;

  const priorityData = [
    { label: 'Critical', value: data.criticalIncidents, color: '#dc2626' },
    { label: 'High', value: data.highPriorityIncidents, color: '#ea580c' },
    { label: 'Medium', value: data.mediumPriorityIncidents, color: '#ca8a04' },
    { label: 'Low', value: data.lowPriorityIncidents, color: '#16a34a' }
  ];

  return (
    <div className="overview-page">
      <Header title="Dashboard Overview" subtitle="Municipal grievance intelligence summary" />
      <div className="page-content">
        <section className="hero-section">
          <div className="workload-transformation">
            <div className="transformation-header">
              <h2>Workload Transformation</h2>
              <span className="insight-badge">Key Insight</span>
            </div>
            <p className="transformation-tagline">Intelligent clustering reduces administrative overhead</p>
            <div className="transformation-visual">
              <div className="transform-block before">
                <div className="block-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div>
                <div className="block-content"><span className="block-value">{data.totalComplaints}</span><span className="block-label">Individual Complaints</span></div>
              </div>
              <div className="transform-arrow"><div className="arrow-line"></div><div className="arrow-badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg><span>{data.workloadReduction}% Reduction</span></div></div>
              <div className="transform-block after">
                <div className="block-icon success"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22,4 12,14.01 9,11.01"/></svg></div>
                <div className="block-content"><span className="block-value">{data.uniqueIncidents}</span><span className="block-label">Unique Incidents</span></div>
              </div>
            </div>
          </div>
        </section>

        <section className="kpi-grid">
          <div className="kpi-card critical"><div className="kpi-header"><span className="kpi-icon">!</span><span className="kpi-title">Critical</span></div><span className="kpi-value">{data.criticalIncidents}</span><span className="kpi-subtitle">Immediate attention</span></div>
          <div className="kpi-card high"><div className="kpi-header"><span className="kpi-icon">!!</span><span className="kpi-title">High Priority</span></div><span className="kpi-value">{data.highPriorityIncidents}</span><span className="kpi-subtitle">Urgent action needed</span></div>
          <div className="kpi-card medium"><div className="kpi-header"><span className="kpi-icon">III</span><span className="kpi-title">Medium</span></div><span className="kpi-value">{data.mediumPriorityIncidents}</span><span className="kpi-subtitle">Scheduled response</span></div>
          <div className="kpi-card low"><div className="kpi-header"><span className="kpi-icon">IV</span><span className="kpi-title">Low</span></div><span className="kpi-value">{data.lowPriorityIncidents}</span><span className="kpi-subtitle">Routine handling</span></div>
          <div className="kpi-card neutral"><div className="kpi-header"><span className="kpi-title">Avg Days Open</span></div><span className="kpi-value">{data.avgDaysOpen}</span><span className="kpi-subtitle">Resolution time</span></div>
          <div className="kpi-card neutral"><div className="kpi-header"><span className="kpi-title">Avg Priority Score</span></div><span className="kpi-value">{data.avgResolutionScore}</span><span className="kpi-subtitle">Out of 100</span></div>
        </section>

        <section className="charts-grid">
          <div className="chart-card">
            <h3>Monthly Complaint Trend</h3>
            <Plot data={[{ x: data.trendData.map(d => d.date), y: data.trendData.map(d => d.complaints), type: 'bar', name: 'Complaints', marker: { color: '#94a3b8' } }, { x: data.trendData.map(d => d.date), y: data.trendData.map(d => d.incidents), type: 'scatter', mode: 'lines+markers', name: 'Incidents', line: { color: '#1e293b', width: 3 }, marker: { size: 8 } }]}
              layout={{ paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', margin: { t: 20, r: 20, b: 40, l: 40 }, xaxis: { showgrid: false, tickangle: -45 }, yaxis: { showgrid: true, gridcolor: '#f1f5f9' }, barmode: 'group', bargap: 0.3, showlegend: true, legend: { orientation: 'h', y: 1.1 }, height: 280 }}
              config={{ displayModeBar: false, responsive: true }} style={{ width: '100%' }} />
          </div>

          <div className="chart-card">
            <h3>Priority Distribution</h3>
            <Plot data={[{ values: priorityData.map(d => d.value), labels: priorityData.map(d => d.label), type: 'pie', hole: 0.5, marker: { colors: priorityData.map(d => d.color) }, textinfo: 'value', textposition: 'inside', textfont: { size: 14 } }]}
              layout={{ paper_bgcolor: 'transparent', margin: { t: 20, r: 20, b: 20, l: 20 }, showlegend: true, legend: { orientation: 'h', y: -0.1 }, annotations: [{ text: `${data.uniqueIncidents}`, showarrow: false, font: { size: 28 } }], height: 280 }}
              config={{ displayModeBar: false, responsive: true }} style={{ width: '100%' }} />
          </div>

          <div className="chart-card">
            <h3>Category Breakdown</h3>
            <Plot data={[{ x: data.categoryBreakdown.map(d => d.count), y: data.categoryBreakdown.map(d => d.category), type: 'bar', orientation: 'h', marker: { color: data.categoryBreakdown.map(d => d.color) }, text: data.categoryBreakdown.map(d => d.count), textposition: 'outside' }]}
              layout={{ paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', margin: { t: 20, r: 40, b: 30, l: 120 }, xaxis: { showgrid: true, gridcolor: '#f1f5f9' }, yaxis: { showgrid: false }, height: 240 }}
              config={{ displayModeBar: false, responsive: true }} style={{ width: '100%' }} />
          </div>

          <div className="chart-card">
            <h3>Ward-wise Distribution</h3>
            <div className="ward-list">{data.wardBreakdown.slice(0, 6).map((ward, i) => (<div key={i} className="ward-item"><span className="ward-name">{ward.ward}</span><div className="ward-bar-container"><div className="ward-bar" style={{ width: `${(ward.count / data.totalComplaints) * 100}%` }}></div></div><span className="ward-count">{ward.count}</span></div>))}</div>
          </div>
        </section>

        <section className="recent-section">
          <div className="section-header"><h3>Top Priority Incidents</h3><a href="/incidents" className="view-all">View All Incidents</a></div>
          <div className="recent-incidents">{data.recentIncidents.map(incident => (<div key={incident.id} className={`recent-incident priority-${incident.priority_label.toLowerCase()}`}><div className="incident-header"><span className="incident-id">{incident.incident_number}</span><span className={`priority-badge ${incident.priority_label.toLowerCase()}`}>{incident.priority_label}</span></div><p className="incident-summary">{incident.summary}</p><div className="incident-meta"><span>{incident.ward.split(' - ')[1]}</span><span>{incident.cluster_size} complaints</span><span>{incident.days_open} days open</span></div></div>))}</div>
        </section>
      </div>
    </div>
  );
};

export default Overview;
