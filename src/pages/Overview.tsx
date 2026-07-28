import { useState, useEffect, useCallback } from 'react';
import { useDashboardSocket } from '../hooks/useDashboardSocket';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import Header from '../components/Header';
import KPICard from '../components/KPICard';
import { AlertTriangle, Clock, Activity, Target, ListChecks } from 'lucide-react';
import { AgingBadge } from '../components/AgingBadge';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import './Overview.css';

interface BackendDashboardData {
  totalComplaints: number;
  uniqueIncidents: number;
  workloadReduction: number;
  criticalIncidents: number;
  highPriorityIncidents: number;
  mediumPriorityIncidents: number;
  lowPriorityIncidents: number;
  trendData: { date: string; complaints: number; incidents: number }[];
  categoryBreakdown: { category: string; count: number; color: string }[];
  wardBreakdown: { ward: string; count: number }[];
  recentIncidents: any[];
}

const Overview = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [data, setData] = useState<BackendDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [todayTasks, setTodayTasks] = useState<{ open_today: number; resolved_today: number; new_today: number } | null>(null);

  const fetchDashboard = useCallback(async (showLoader = false) => {
    if (showLoader) setLoading(true);
    try {
      const [res, tasks] = await Promise.all([
        api.getDashboardData(),
        user?.role === 'Officer' ? api.getTodayTasks().catch(() => null) : Promise.resolve(null),
      ]);
      setData(res as BackendDashboardData);
      if (tasks) setTodayTasks(tasks);
    } catch (err: any) {
      if (showLoader) {
        console.error('Failed to fetch dashboard data:', err);
        setError(err.message || 'Failed to load dashboard data');
      }
    } finally {
      if (showLoader) setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    let mounted = true;
    const fetchWithMount = async (showLoader: boolean) => {
      if (!mounted) return;
      await fetchDashboard(showLoader);
    };
    fetchWithMount(true);
    const interval = setInterval(() => fetchWithMount(false), 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, [fetchDashboard]);

  useDashboardSocket({
    onEvent: () => { fetchDashboard(false); },
  });

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>Loading dashboard...</span></div>;
  if (!data) return <div className="page-error">Error: {error || 'Failed to load dashboard data'}</div>;

  const priorityColors = {
    Critical: '#dc2626',
    High: '#ea580c',
    Medium: '#ca8a04',
    Low: '#16a34a'
  };

  const priorityChartData = [
    { label: 'Critical', value: data?.criticalIncidents ?? 0, color: priorityColors.Critical },
    { label: 'High', value: data?.highPriorityIncidents ?? 0, color: priorityColors.High },
    { label: 'Medium', value: data?.mediumPriorityIncidents ?? 0, color: priorityColors.Medium },
    { label: 'Low', value: data?.lowPriorityIncidents ?? 0, color: priorityColors.Low },
  ];

  const hasTrend = data.trendData && data.trendData.length > 0;
  const hasCategory = data.categoryBreakdown && data.categoryBreakdown.length > 0;
  const hasRecent = data.recentIncidents && data.recentIncidents.length > 0;

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
                <div className="block-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div>
                <div className="block-content"><span className="block-value">{data.totalComplaints}</span><span className="block-label">Individual Complaints</span></div>
              </div>
              <div className="transform-arrow"><div className="arrow-line"></div><div className="arrow-badge"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg><span>{data.workloadReduction}% Reduction</span></div></div>
              <div className="transform-block after">
                <div className="block-icon success"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22,4 12,14.01 9,11.01"/></svg></div>
                <div className="block-content"><span className="block-value">{data.uniqueIncidents}</span><span className="block-label">Unique Incidents</span></div>
              </div>
            </div>
          </div>
        </section>

        <section className="kpi-grid">
          <KPICard title="Critical" value={data.criticalIncidents} subtitle="Immediate attention" variant="critical" icon={AlertTriangle} />
          <KPICard title="High Priority" value={data.highPriorityIncidents} subtitle="Urgent action needed" icon={Clock} />
          <KPICard title="Medium" value={data.mediumPriorityIncidents} subtitle="Scheduled response" icon={Activity} />
          <KPICard title="Low" value={data.lowPriorityIncidents} subtitle="Routine handling" icon={Target} variant="success" />
        </section>

        {user?.role === 'Officer' && (
          <section className="today-tasks-card">
            <div className="today-tasks-header">
              <ListChecks size={20} />
              <h3>{t('overview.todayTasks')}</h3>
            </div>
            <div className="today-tasks-grid">
              <div className="task-stat">
                <span className="task-value">{todayTasks?.open_today ?? '—'}</span>
                <span className="task-label">{t('overview.openToday')}</span>
              </div>
              <div className="task-stat">
                <span className="task-value resolved">{todayTasks?.resolved_today ?? '—'}</span>
                <span className="task-label">{t('overview.resolvedToday')}</span>
              </div>
              <div className="task-stat">
                <span className="task-value new">{todayTasks?.new_today ?? '—'}</span>
                <span className="task-label">{t('overview.newToday')}</span>
              </div>
            </div>
          </section>
        )}

        <section className="charts-grid">
          <div className="chart-card">
            <h3>Priority Distribution</h3>
            <Plot data={[{ values: priorityChartData.map(d => d.value), labels: priorityChartData.map(d => d.label), type: 'pie', hole: 0.5, marker: { colors: priorityChartData.map(d => d.color) }, textinfo: 'value', textposition: 'inside', textfont: { size: 14 } }]}
              layout={{ paper_bgcolor: 'transparent', margin: { t: 20, r: 20, b: 20, l: 20 }, showlegend: true, legend: { orientation: 'h', y: -0.1 }, annotations: [{ text: `${data.uniqueIncidents}`, showarrow: false, font: { size: 28 } }], height: 280 }}
              config={{ displayModeBar: false, responsive: true }} style={{ width: '100%' }} />
          </div>

          <div className="chart-card">
            <h3>Category Breakdown</h3>
            {hasCategory ? (
              <Plot data={[{ x: data.categoryBreakdown.map(d => d.count), y: data.categoryBreakdown.map(d => d.category), type: 'bar', orientation: 'h', marker: { color: data.categoryBreakdown.map(d => d.color) }, text: data.categoryBreakdown.map(d => d.count), textposition: 'outside' }]}
                layout={{ paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', margin: { t: 20, r: 40, b: 30, l: 120 }, xaxis: { showgrid: true, gridcolor: '#f1f5f9' }, yaxis: { showgrid: false }, height: 280 }}
                config={{ displayModeBar: false, responsive: true }} style={{ width: '100%' }} />
            ) : (
              <div className="empty-chart">No category data available.</div>
            )}
          </div>
        </section>
        
        <section className="recent-incidents-card">
          <h3>Recent Incidents</h3>
          <div className="table-container">
            {hasRecent ? (
              <table>
                <thead>
                  <tr>
                    <th>Incident ID</th>
                    <th>Category</th>
                    <th>Ward</th>
                    <th>Days</th>
                    <th>Priority</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recentIncidents.map((inc: any) => (
                    <tr key={inc.id}>
                      <td>{inc.incident_number}</td>
                      <td>{inc.category}</td>
                      <td>{inc.ward}</td>
                      <td><AgingBadge daysOpen={inc.days_open ?? 0} /></td>
                      <td><span className={`badge ${inc.priority_label?.toLowerCase() ?? 'low'}`}>{inc.priority_label ?? 'N/A'}</span></td>
                      <td>{inc.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>No recent incidents available.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

export default Overview;
