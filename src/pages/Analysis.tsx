import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import Header from '../components/Header';
import { AlertCircle } from 'lucide-react';
import './Analysis.css';

interface CategoryItem {
  category: string;
  count: number;
}

interface DeptItem {
  department: string;
  activeIncidents: number;
}

interface WardItem {
  ward: string;
  complaintCount: number;
}

interface Overview {
  totalComplaints: number;
  totalIncidents: number;
  openIncidents: number;
}

interface AnalyticsData {
  overview: Overview;
  categoryBreakdown: CategoryItem[];
  departmentWorkload: DeptItem[];
  volumeTrend: { labels: string[]; complaints: number[]; incidents: number[] };
  resolutionTrend: { labels: string[]; avgDays: (number | null)[] };
  wardHotspots: WardItem[];
}

const Analysis = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getAnalytics()
      .then(d => { if (!cancelled) setData(d); })
      .catch(e => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="page-loading"><div className="spinner" /><span>{t('analysis.loading')}</span></div>;
  if (error) return <div className="page-error"><AlertCircle size={20} /> {error}</div>;
  if (!data) return null;

  const { overview, categoryBreakdown, departmentWorkload, volumeTrend, resolutionTrend, wardHotspots } = data;

  const color = (i: number, base = 210) => `hsl(${base + i * 30}, 65%, 55%)`;

  return (
    <div className="analysis-page">
      <Header title={t('analysis.pageTitle')} subtitle={t('analysis.pageSubtitle')} />
      <div className="page-content">

        <div className="kpi-hero">
          <div className="kpi-card">
            <span className="kpi-value">{overview.totalComplaints.toLocaleString()}</span>
            <span className="kpi-label">{t('analysis.totalComplaints')}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-value">{overview.totalIncidents.toLocaleString()}</span>
            <span className="kpi-label">{t('analysis.totalIncidents')}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-value">{overview.openIncidents.toLocaleString()}</span>
            <span className="kpi-label">{t('analysis.openIncidents')}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-value">{categoryBreakdown.length}</span>
            <span className="kpi-label">{t('analysis.categoriesTracked')}</span>
          </div>
        </div>

        <div className="chart-grid">
          <div className="chart-card chart-full">
            <div className="chart-hdr">
              <h3>{t('analysis.volumeTrendTitle')}</h3>
              <span className="chart-desc">{t('analysis.volumeTrendSubtitle')}</span>
            </div>
            <Plot
              data={[
                { x: volumeTrend.labels, y: volumeTrend.complaints, type: 'scatter', mode: 'lines+markers',
                  name: t('analysis.complaints'), line: { color: '#3b82f6', width: 2 }, marker: { size: 5 } },
                { x: volumeTrend.labels, y: volumeTrend.incidents, type: 'scatter', mode: 'lines+markers',
                  name: t('analysis.incidents'), line: { color: '#8b5cf6', width: 2 }, marker: { size: 5 } },
              ]}
              layout={{
                autosize: true, height: 280,
                paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#94a3b8', size: 11 },
                margin: { t: 10, b: 40, l: 50, r: 10 },
                legend: { orientation: 'h', y: 1.1, x: 0 },
                xaxis: { gridcolor: 'rgba(255,255,255,0.05)' },
                yaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false },
              }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: '100%' }}
            />
          </div>
        </div>

        <div className="chart-grid chart-grid-2">
          <div className="chart-card">
            <div className="chart-hdr">
              <h3>{t('analysis.categoryBreakdownTitle')}</h3>
              <span className="chart-desc">{t('analysis.categoryBreakdownSubtitle')}</span>
            </div>
            {categoryBreakdown.length === 0 ? (
              <p className="empty-chart">{t('analysis.noData')}</p>
            ) : (
              <Plot
                data={[{
                  x: categoryBreakdown.map(c => c.count),
                  y: categoryBreakdown.map(c => c.category),
                  type: 'bar', orientation: 'h',
                  marker: { color: categoryBreakdown.map((_, i) => color(i)) },
                }]}
                layout={{
                  autosize: true, height: Math.max(180, categoryBreakdown.length * 38),
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#94a3b8', size: 11 },
                  margin: { t: 10, b: 40, l: 130, r: 20 },
                  xaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false },
                  yaxis: { automargin: true },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            )}
          </div>

          <div className="chart-card">
            <div className="chart-hdr">
              <h3>{t('analysis.resolutionTrendTitle')}</h3>
              <span className="chart-desc">{t('analysis.resolutionTrendSubtitle')}</span>
            </div>
            <Plot
              data={[{
                x: resolutionTrend.labels,
                y: resolutionTrend.avgDays.map(d => d ?? 0),
                type: 'scatter', mode: 'lines+markers',
                name: t('analysis.avgDays'),
                line: { color: '#16a34a', width: 2 },
                marker: { size: 5 },
                connectgaps: false,
              }]}
              layout={{
                autosize: true, height: 240,
                paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#94a3b8', size: 11 },
                margin: { t: 10, b: 40, l: 50, r: 10 },
                xaxis: { gridcolor: 'rgba(255,255,255,0.05)' },
                yaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false, ticksuffix: 'd' },
              }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: '100%' }}
            />
          </div>
        </div>

        <div className="chart-grid">
          <div className="chart-card chart-full">
            <div className="chart-hdr">
              <h3>{t('analysis.deptWorkloadTitle')}</h3>
              <span className="chart-desc">{t('analysis.deptWorkloadSubtitle')}</span>
            </div>
            {departmentWorkload.length === 0 ? (
              <p className="empty-chart">{t('analysis.noData')}</p>
            ) : (
              <Plot
                data={[{
                  x: departmentWorkload.map(d => d.activeIncidents),
                  y: departmentWorkload.map(d => d.department),
                  type: 'bar', orientation: 'h',
                  marker: { color: '#f59e0b' },
                }]}
                layout={{
                  autosize: true, height: Math.max(200, departmentWorkload.length * 45),
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#94a3b8', size: 11 },
                  margin: { t: 10, b: 40, l: 200, r: 40 },
                  xaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false },
                  yaxis: { automargin: true },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            )}
          </div>
        </div>

        <div className="chart-grid">
          <div className="chart-card chart-full">
            <div className="chart-hdr">
              <h3>{t('analysis.wardHotspotsTitle')}</h3>
              <span className="chart-desc">{t('analysis.wardHotspotsSubtitle')}</span>
            </div>
            {wardHotspots.length === 0 ? (
              <p className="empty-chart">{t('analysis.noData')}</p>
            ) : (
              <Plot
                data={[{
                  x: wardHotspots.map(w => w.ward),
                  y: wardHotspots.map(w => w.complaintCount),
                  type: 'bar',
                  marker: {
                    color: wardHotspots.map(w =>
                      w.complaintCount >= 5 ? '#dc2626' :
                      w.complaintCount >= 3 ? '#f59e0b' : '#3b82f6'
                    ),
                  },
                }]}
                layout={{
                  autosize: true, height: Math.max(220, wardHotspots.length * 32),
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#94a3b8', size: 11 },
                  margin: { t: 10, b: 80, l: 100, r: 20 },
                  xaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false, tickangle: -30 },
                  yaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default Analysis;
