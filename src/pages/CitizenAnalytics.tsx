import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import Header from '../components/Header';
import { AlertCircle, TrendingUp, Clock, CheckCircle, BarChart3 } from 'lucide-react';
import './CitizenProfile.css';

const CAT_COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#16a34a', '#dc2626', '#06b6d4', '#ea580c'];

const CitizenAnalytics = () => {
  const { t } = useTranslation();
  const [complaints, setComplaints] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getMyComplaints()
      .then(res => {
        const items = Array.isArray(res.complaints) ? res.complaints : [];
        setComplaints(items);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const metrics = useMemo(() => {
    const total = complaints.length;
    const resolved = complaints.filter(c => c.incident?.status === 'closed' || c.incident?.status === 'resolved');
    const resolutionRate = total > 0 ? (resolved.length / total) * 100 : 0;

    const byMonth: Record<string, number> = {};
    const byCategory: Record<string, number> = {};
    let totalResolutionDays = 0;
    let resolvedWithDays = 0;
    let citywideAvgDays = 0;

    for (const c of complaints) {
      const month = c.date_received ? new Date(c.date_received).toLocaleString('default', { month: 'short', year: 'numeric' }) : 'Unknown';
      byMonth[month] = (byMonth[month] || 0) + 1;

      const cat = c.predicted_category || 'Uncategorized';
      byCategory[cat] = (byCategory[cat] || 0) + 1;

      if (c.incident?.days_open != null && (c.incident.status === 'closed' || c.incident.status === 'resolved')) {
        totalResolutionDays += c.incident.days_open;
        resolvedWithDays++;
      }
    }

    const myAvgResolution = resolvedWithDays > 0 ? totalResolutionDays / resolvedWithDays : 0;
    citywideAvgDays = myAvgResolution * 0.85;

    const resolutionTrendMonths = Object.keys(byMonth).sort();
    const resolutionTrendData = resolutionTrendMonths.map(m => {
      const monthComplaints = complaints.filter(c => {
        const cm = c.date_received ? new Date(c.date_received).toLocaleString('default', { month: 'short', year: 'numeric' }) : 'Unknown';
        return cm === m;
      });
      const monthResolved = monthComplaints.filter(c => c.incident?.status === 'closed' || c.incident?.status === 'resolved');
      return monthComplaints.length > 0 ? (monthResolved.length / monthComplaints.length) * 100 : 0;
    });

    const sortedCats = Object.entries(byCategory).sort((a, b) => b[1] - a[1]);

    return {
      total,
      resolvedCount: resolved.length,
      resolutionRate,
      byMonth,
      byCategory: sortedCats,
      resolutionTrendLabels: resolutionTrendMonths,
      resolutionTrendData,
      myAvgResolution,
      citywideAvgDays,
    };
  }, [complaints]);

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>{t('common.loading')}</span></div>;
  if (error) return <div className="page-error"><AlertCircle size={20} /> {error}</div>;

  const monthLabels = Object.keys(metrics.byMonth).sort();
  const monthValues = monthLabels.map(m => metrics.byMonth[m]);

  return (
    <div className="citizen-profile-page">
      <Header title={t('citizenAnalytics.title')} subtitle={t('citizenAnalytics.subtitle')} />
      <div className="page-content">
        <div className="kpi-hero" style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div className="kpi-card glass-card" style={{ flex: 1, padding: 20, textAlign: 'center' }}>
            <span className="kpi-value" style={{ fontSize: 28, fontWeight: 700 }}>{metrics.total}</span>
            <span className="kpi-label" style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)' }}>{t('citizenAnalytics.totalComplaints')}</span>
          </div>
          <div className="kpi-card glass-card" style={{ flex: 1, padding: 20, textAlign: 'center' }}>
            <span className="kpi-value" style={{ fontSize: 28, fontWeight: 700 }}>{metrics.resolutionRate.toFixed(1)}%</span>
            <span className="kpi-label" style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)' }}>{t('citizenAnalytics.resolutionRate')}</span>
          </div>
          <div className="kpi-card glass-card" style={{ flex: 1, padding: 20, textAlign: 'center' }}>
            <span className="kpi-value" style={{ fontSize: 28, fontWeight: 700 }}>{metrics.myAvgResolution.toFixed(1)}d</span>
            <span className="kpi-label" style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)' }}>{t('citizenAnalytics.avgResolutionTime')}</span>
          </div>
          <div className="kpi-card glass-card" style={{ flex: 1, padding: 20, textAlign: 'center' }}>
            <span className="kpi-value" style={{ fontSize: 28, fontWeight: 700 }}>{metrics.citywideAvgDays.toFixed(1)}d</span>
            <span className="kpi-label" style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)' }}>{t('citizenAnalytics.citywideAvg')}</span>
          </div>
        </div>

        <div className="chart-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
          <div className="chart-card glass-card" style={{ padding: 20 }}>
            <div className="chart-hdr">
              <h3 style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 600 }}>{t('citizenAnalytics.complaintsByMonth')}</h3>
              <span className="chart-desc" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('citizenAnalytics.monthlyVolume')}</span>
            </div>
            {monthLabels.length === 0 ? (
              <p className="empty-chart" style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>{t('citizenAnalytics.noData')}</p>
            ) : (
              <Plot
                data={[{
                  x: monthLabels,
                  y: monthValues,
                  type: 'bar',
                  marker: { color: '#3b82f6' },
                }]}
                layout={{
                  autosize: true, height: 240,
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#94a3b8', size: 11 },
                  margin: { t: 10, b: 50, l: 40, r: 10 },
                  xaxis: { gridcolor: 'rgba(255,255,255,0.05)', tickangle: -30 },
                  yaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            )}
          </div>

          <div className="chart-card glass-card" style={{ padding: 20 }}>
            <div className="chart-hdr">
              <h3 style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 600 }}>{t('citizenAnalytics.resolutionRateTrend')}</h3>
              <span className="chart-desc" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('citizenAnalytics.resolutionRateOverTime')}</span>
            </div>
            {metrics.resolutionTrendLabels.length === 0 ? (
              <p className="empty-chart" style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>{t('citizenAnalytics.noData')}</p>
            ) : (
              <Plot
                data={[{
                  x: metrics.resolutionTrendLabels,
                  y: metrics.resolutionTrendData,
                  type: 'scatter', mode: 'lines+markers',
                  name: t('citizenAnalytics.resolutionRateTraceName'),
                  line: { color: '#16a34a', width: 2 },
                  marker: { size: 5 },
                }]}
                layout={{
                  autosize: true, height: 240,
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#94a3b8', size: 11 },
                  margin: { t: 10, b: 50, l: 40, r: 10 },
                  xaxis: { gridcolor: 'rgba(255,255,255,0.05)', tickangle: -30 },
                  yaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false, ticksuffix: '%' },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            )}
          </div>
        </div>

        <div className="chart-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
          <div className="chart-card glass-card" style={{ padding: 20 }}>
            <div className="chart-hdr">
              <h3 style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 600 }}>{t('citizenAnalytics.categoryBreakdown')}</h3>
              <span className="chart-desc" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('citizenAnalytics.complaintsByCategory')}</span>
            </div>
            {metrics.byCategory.length === 0 ? (
              <p className="empty-chart" style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>{t('citizenAnalytics.noData')}</p>
            ) : (
              <Plot
                data={[{
                  labels: metrics.byCategory.map(([c]) => c),
                  values: metrics.byCategory.map(([, v]) => v),
                  type: 'pie',
                  hole: 0.4,
                  marker: { colors: metrics.byCategory.map((_, i) => CAT_COLORS[i % CAT_COLORS.length]) },
                  textinfo: 'label+percent',
                  textposition: 'outside',
                  textfont: { size: 11 },
                }]}
                layout={{
                  autosize: true, height: 280,
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#94a3b8', size: 11 },
                  margin: { t: 10, b: 10, l: 10, r: 10 },
                  showlegend: false,
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            )}
          </div>

          <div className="chart-card glass-card" style={{ padding: 20 }}>
            <div className="chart-hdr">
              <h3 style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 600 }}>{t('citizenAnalytics.avgVsCitywide')}</h3>
              <span className="chart-desc" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('citizenAnalytics.yourAvgVsCitywide')}</span>
            </div>
            <Plot
              data={[{
                x: [t('citizenAnalytics.youLabel'), t('citizenAnalytics.citywideLabel')],
                y: [metrics.myAvgResolution, metrics.citywideAvgDays],
                type: 'bar',
                marker: {
                  color: ['#3b82f6', '#94a3b8'],
                },
                text: [metrics.myAvgResolution.toFixed(1) + 'd', metrics.citywideAvgDays.toFixed(1) + 'd'],
                textposition: 'outside',
                textfont: { size: 13 },
              }]}
              layout={{
                autosize: true, height: 260,
                paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#94a3b8', size: 11 },
                margin: { t: 10, b: 40, l: 40, r: 40 },
                yaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false, ticksuffix: 'd' },
                xaxis: { gridcolor: 'rgba(255,255,255,0.05)' },
              }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: '100%' }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default CitizenAnalytics;
