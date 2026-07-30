import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import Header from '../components/Header';
import { AlertCircle } from 'lucide-react';
import { getDeptI18nKey } from '../data/departments';
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
  categoryTrend?: { month: string; category: string; count: number }[];
}

interface QualityItem {
  bucket: string;
  count: number;
  avg_resolution_days: number;
}

const Analysis = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [qualityData, setQualityData] = useState<QualityItem[] | null>(null);
  const [dailyVolume, setDailyVolume] = useState<any>(null);
  const [ageDistribution, setAgeDistribution] = useState<any>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [d, q] = await Promise.all([
          api.getAnalytics(),
          api.getComplaintQuality().catch(() => null),
        ]);
        if (!cancelled) { setData(d); if (q) setQualityData(q.distribution); }

        // FEATURE 1: daily volume
        try {
          const dv = await api.getDailyVolume(90);
          if (typeof dv === 'object' && !dv.error) setDailyVolume(dv);
        } catch {}

        // FEATURE 14: age distribution
        try {
          const ad = await api.get('/admin/zone-age-distribution');
          const adData = await ad.json();
          if (adData && typeof adData === 'object') {
            const buckets = [
              { label: t('analysis.fresh'), from: 0, to: 7 },
              { label: t('analysis.developing'), from: 7, to: 30 },
              { label: t('analysis.chronic'), from: 30, to: 90 },
              { label: t('analysis.criticalBacklog'), from: 90, to: Infinity },
            ];
            const allIncidents = Object.values(adData).flatMap((z: any) => z.buckets ? Object.entries(z.buckets).map(([k, v]) => ({ label: k, count: v })) : []);
            setAgeDistribution(buckets.map(b => ({
              label: b.label,
              count: allIncidents.filter(i => {
                const days = parseInt(i.label) || 0;
                return days >= b.from && days < b.to;
              }).reduce((s, i) => s + (typeof i.count === 'number' ? i.count : 0), 0)
            })));
          }
        } catch {}
      } catch (e) {
        if (!cancelled) setError((e as any)?.message || 'Unknown error');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
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
                  y: departmentWorkload.map(d => t(getDeptI18nKey(d.department))),
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

        {data.categoryTrend && data.categoryTrend.length > 0 && (() => {
          const categories = [...new Set(data.categoryTrend.map(d => d.category))];
          const months = [...new Set(data.categoryTrend.map(d => d.month))].sort();
          const color = (i: number) => `hsl(${(i * 45) % 360}, 60%, 55%)`;
          const traces = categories.map((cat, i) => ({
            x: months,
            y: months.map(m => {
              const found = data.categoryTrend!.find(d => d.month === m && d.category === cat);
              return found ? found.count : 0;
            }),
            type: 'scatter',
            mode: 'lines+markers',
            name: cat,
            line: { color: color(i), width: 2 },
            marker: { size: 4 },
          }));
          return (
            <div className="chart-grid">
              <div className="chart-card chart-full">
                <div className="chart-hdr">
                  <h3>{t('analysis.categoryTrendTitle')}</h3>
                  <span className="chart-desc">{t('analysis.categoryTrendSubtitle')}</span>
                </div>
                <Plot
                  data={traces}
                  layout={{
                    autosize: true, height: 280,
                    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#94a3b8', size: 11 },
                    margin: { t: 10, b: 40, l: 50, r: 10 },
                    legend: { orientation: 'h', y: 1.1, x: 0, font: { size: 10 } },
                    xaxis: { gridcolor: 'rgba(255,255,255,0.05)' },
                    yaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false },
                  }}
                  config={{ displayModeBar: false, responsive: true }}
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          );
        })()}

        {qualityData && qualityData.length > 0 && (
          <div className="chart-grid">
            <div className="chart-card chart-full">
              <div className="chart-hdr">
                <h3>{t('analysis.complaintQualityTitle')}</h3>
                <span className="chart-desc">{t('analysis.complaintQualitySubtitle')}</span>
              </div>
              <div className="quality-bars">
                {qualityData.map((item, i) => {
                  const maxCount = Math.max(...qualityData.map(q => q.count));
                  const pct = maxCount > 0 ? (item.count / maxCount) * 100 : 0;
                  return (
                    <div key={i} className="quality-bar-row">
                      <span className="quality-bar-label">{item.bucket}</span>
                      <div className="quality-bar-track">
                        <div className="quality-bar-fill" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="quality-bar-count">{item.count}</span>
                      <span className="quality-bar-days">{item.avg_resolution_days}d</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

      {/* FEATURE 1: Severity Heatmap Calendar */}
      {dailyVolume && Object.keys(dailyVolume).length > 0 && (
        <div className="chart-card">
          <h3>{t('analysis.severityHeatmap')}</h3>
          <p className="chart-subtitle">{t('analysis.last90Days')}</p>
          <div className="heatmap-calendar">
            {(() => {
              const today = new Date();
              const cells = [];
              for (let i = 89; i >= 0; i--) {
                const d = new Date(today);
                d.setDate(d.getDate() - i);
                const key = d.toISOString().split('T')[0];
                const count = dailyVolume[key] || 0;
                let color = '#ebedf0';
                if (count > 20) color = '#216e39';
                else if (count > 10) color = '#30a14e';
                else if (count > 5) color = '#9be9a8';
                else if (count > 0) color = '#c6e48b';
                cells.push(
                  <div
                    key={key}
                    className="heatmap-cell"
                    style={{ backgroundColor: color }}
                    title={`${key}: ${count} complaints`}
                  />
                );
              }
              return cells;
            })()}
          </div>
        </div>
      )}

      {/* FEATURE 14: Age Distribution Pie */}
      {ageDistribution && ageDistribution.length > 0 && (
        <div className="chart-card">
          <h3>{t('analysis.ageDistribution')}</h3>
          <Plot
            data={[{
              type: 'pie',
              labels: ageDistribution.map((a: any) => a.label),
              values: ageDistribution.map((a: any) => a.count),
              marker: { colors: ['#22c55e', '#eab308', '#f97316', '#ef4444'] },
              textinfo: 'label+percent',
            }]}
            layout={{ height: 350, margin: { t: 20, r: 20, b: 40, l: 40 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#e2e8f0' }, showlegend: true }}
            config={{ responsive: true, displayModeBar: false }}
          />
        </div>
      )}

      </div>
    </div>
  );
};

export default Analysis;
