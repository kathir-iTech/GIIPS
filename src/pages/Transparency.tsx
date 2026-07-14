import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import { ArrowLeft, AlertCircle, Loader2 } from 'lucide-react';
import './Transparency.css';

interface CategoryStat {
  category: string;
  count: number;
}

interface ZoneStat {
  zone: string;
  count: number;
}

interface StatsData {
  totalComplaintsThisMonth: number;
  resolutionRate: number;
  avgResolutionDays: number;
  complaintsByCategory: CategoryStat[];
  complaintsByZone: ZoneStat[];
}

const ZONE_COLORS: Record<string, string> = {
  North: '#3b82f6',
  South: '#16a34a',
  East: '#f59e0b',
  West: '#8b5cf6',
  Central: '#dc2626',
};

const COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#16a34a', '#dc2626', '#06b6d4', '#ea580c'];

const Transparency = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getPublicStats()
      .then(d => { if (!cancelled) setData(d); })
      .catch(e => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return (
    <div className="transparency-page">
      <div className="transparency-container">
        <div className="page-loading"><Loader2 size={32} className="spin" /><span>{t('transparency.loading')}</span></div>
      </div>
    </div>
  );

  if (error) return (
    <div className="transparency-page">
      <div className="transparency-container">
        <div className="page-error"><AlertCircle size={20} /> {error}</div>
      </div>
    </div>
  );

  return (
    <div className="transparency-page">
      <div className="transparency-container">
        <Link to="/" className="track-back"><ArrowLeft size={16} /> {t('transparency.backButton')}</Link>

        <div className="transparency-header">
          <h1>{t('transparency.title')}</h1>
          <p>{t('transparency.subtitle')}</p>
        </div>

        <div className="kpi-hero">
          <div className="kpi-card">
            <span className="kpi-value">{(data?.totalComplaintsThisMonth ?? 0).toLocaleString()}</span>
            <span className="kpi-label">{t('transparency.kpiComplaintsMonth')}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-value">{data?.resolutionRate ?? 0}%</span>
            <span className="kpi-label">{t('transparency.kpiResolutionRate')}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-value">{data?.avgResolutionDays ?? 0}</span>
            <span className="kpi-label">{t('transparency.kpiAvgDays')}</span>
          </div>
        </div>

        <div className="chart-grid chart-grid-2">
          <div className="chart-card">
            <div className="chart-hdr">
              <h3>{t('transparency.categoryChartTitle')}</h3>
              <span className="chart-desc">{t('transparency.categoryChartSubtitle')}</span>
            </div>
            {(!data?.complaintsByCategory || data.complaintsByCategory.length === 0) ? (
              <p className="empty-chart">{t('transparency.noData')}</p>
            ) : (
              <Plot
                data={[{
                  x: data.complaintsByCategory.map(c => c.count),
                  y: data.complaintsByCategory.map(c => c.category),
                  type: 'bar', orientation: 'h',
                  marker: { color: data.complaintsByCategory.map((_, i) => COLORS[i % COLORS.length]) },
                }]}
                layout={{
                  autosize: true, height: Math.max(180, data.complaintsByCategory.length * 38),
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
              <h3>{t('transparency.zoneChartTitle')}</h3>
              <span className="chart-desc">{t('transparency.zoneChartSubtitle')}</span>
            </div>
            {(!data?.complaintsByZone || data.complaintsByZone.length === 0) ? (
              <p className="empty-chart">{t('transparency.noData')}</p>
            ) : (
              <Plot
                data={[{
                  labels: data.complaintsByZone.map(z => z.zone),
                  values: data.complaintsByZone.map(z => z.count),
                  type: 'pie',
                  marker: {
                    colors: data.complaintsByZone.map(z => ZONE_COLORS[z.zone] || '#64748b'),
                  },
                  textinfo: 'label+percent',
                  textposition: 'outside',
                }]}
                layout={{
                  autosize: true, height: 280,
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#94a3b8', size: 11 },
                  margin: { t: 10, b: 40, l: 10, r: 10 },
                  showlegend: false,
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

export default Transparency;
