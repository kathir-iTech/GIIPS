import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import { ArrowLeft, AlertCircle, Loader2, Star, Clock, Building2, MapPin, Search } from 'lucide-react';
import './Transparency.css';

interface CategoryStat {
  category: string;
  count: number;
}

interface ZoneStat {
  zone: string;
  count: number;
}

interface HourStat {
  hour: number;
  count: number;
}

interface DayStat {
  day: string;
  count: number;
}

interface FunnelStage {
  label: string;
  count: number;
}

interface StatsData {
  totalComplaintsThisMonth: number;
  resolutionRate: number;
  avgResolutionDays: number;
  complaintsByCategory: CategoryStat[];
  complaintsByZone: ZoneStat[];
  complaintsByHour: HourStat[];
  complaintsByDay: DayStat[];
  complaintsByStatus: FunnelStage[];
}

const ZONE_COLORS: Record<string, string> = {
  North: '#3b82f6',
  South: '#16a34a',
  East: '#f59e0b',
  West: '#8b5cf6',
  Central: '#dc2626',
};

const COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#16a34a', '#dc2626', '#06b6d4', '#ea580c'];

interface SuccessStory {
  category: string;
  ward: string;
  department: string;
  resolution_note: string | null;
  citizen_rating: number;
  days_to_resolve: number;
}

interface WardStats {
  ward: string;
  total_complaints: number;
  resolved_percentage: number;
  avg_resolution_days: number;
  top_categories: { category: string; count: number }[];
}

const Transparency = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<StatsData | null>(null);
  const [stories, setStories] = useState<SuccessStory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wardInput, setWardInput] = useState('');
  const [wardStats, setWardStats] = useState<WardStats | null>(null);
  const [wardLoading, setWardLoading] = useState(false);
  const [wardError, setWardError] = useState<string | null>(null);
  const [satisfactionData, setSatisfactionData] = useState<any[]>([]);
  const [wordCloud, setWordCloud] = useState<any[]>([]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.getPublicStats(),
      api.getSuccessStories(),
      api.get('/public/satisfaction-trend').then(r => r.json()).catch(() => []),
      api.get('/public/word-cloud').then(r => r.json()).catch(() => []),
    ]).then(([stats, successStories, satData, wcData]) => {
      if (!cancelled) { setData(stats); setStories(successStories); setSatisfactionData(satData); setWordCloud(wcData); }
    }).catch(e => {
      if (!cancelled) setError(e.message);
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  const handleWardLookup = async () => {
    const w = wardInput.trim();
    if (!w || isNaN(Number(w)) || Number(w) < 1 || Number(w) > 100) return;
    setWardLoading(true);
    setWardError(null);
    setWardStats(null);
    try {
      const stats = await api.getWardStats(w);
      setWardStats(stats);
    } catch (err: any) {
      setWardError(err.message || 'Failed to load ward stats');
    } finally {
      setWardLoading(false);
    }
  };

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

        {data?.complaintsByStatus && data.complaintsByStatus.length > 0 && (
          <div className="funnel-section">
            <div className="funnel-header">
              <h2>{t('transparency.funnelTitle')}</h2>
              <p>{t('transparency.funnelSubtitle')}</p>
            </div>
            <div className="funnel-bar">
              {(() => {
                const stages = data.complaintsByStatus;
                const maxCount = stages[0]?.count || 1;
                const FUNNEL_COLORS = ['#60a5fa', '#3b82f6', '#f59e0b', '#f97316', '#10b981', '#34d399', '#6ee7b7'];
                return stages.map((s, i) => {
                  const pct = (s.count / maxCount) * 100;
                  return (
                    <div key={s.label} className="funnel-row">
                      <span className="funnel-label">{s.label}</span>
                      <div className="funnel-track">
                        <div
                          className="funnel-fill"
                          style={{ width: `${pct}%`, background: FUNNEL_COLORS[i % FUNNEL_COLORS.length] }}
                        />
                      </div>
                      <span className="funnel-count">{s.count.toLocaleString()}</span>
                    </div>
                  );
                });
              })()}
            </div>
          </div>
        )}

        {satisfactionData.length > 0 && (
          <div className="chart-card" style={{ marginTop: '1.5rem' }}>
            <div className="chart-hdr">
              <h3>Citizen Satisfaction Trend</h3>
              <span className="chart-desc">Average citizen rating per week over the last 8 weeks</span>
            </div>
            <Plot
              data={[{x: satisfactionData.map(d=>d.week), y: satisfactionData.map(d=>d.avg_rating), type:'scatter', mode:'lines+markers', marker:{color:'#16a34a'}}]}
              layout={{title:'', width: null, height: 300, autosize: true, paper_bgcolor:'transparent', plot_bgcolor:'transparent', font:{color:'var(--text-primary)'}, margin:{t:10,b:40,l:40,r:10}, xaxis:{gridcolor:'rgba(255,255,255,0.05)'}, yaxis:{gridcolor:'rgba(255,255,255,0.05)',range:[1,5]}}}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: '100%' }}
            />
          </div>
        )}

        <div className="ward-lookup-section">
          <h2><MapPin size={20} /> Ward Stats</h2>
          <p>Enter a ward number (1–100) to view its aggregate complaint data.</p>
          <div className="ward-lookup-row">
            <input
              type="number"
              min={1}
              max={100}
              placeholder="e.g. 12"
              value={wardInput}
              onChange={e => { setWardInput(e.target.value); setWardStats(null); setWardError(null); }}
              onKeyDown={e => e.key === 'Enter' && handleWardLookup()}
              className="ward-input"
              disabled={wardLoading}
            />
            <button className="ward-lookup-btn" onClick={handleWardLookup} disabled={wardLoading || !wardInput.trim()}>
              {wardLoading ? <Loader2 size={16} className="spin" /> : <Search size={16} />} Look Up
            </button>
          </div>
          {wardError && <p className="ward-error">{wardError}</p>}
          {wardStats && (
            <div className="ward-stats-grid">
              <div className="ward-stat-card">
                <span className="ward-stat-value">{wardStats.total_complaints}</span>
                <span className="ward-stat-label">Total Complaints</span>
              </div>
              <div className="ward-stat-card">
                <span className="ward-stat-value">{wardStats.resolved_percentage}%</span>
                <span className="ward-stat-label">Resolved</span>
              </div>
              <div className="ward-stat-card">
                <span className="ward-stat-value">{wardStats.avg_resolution_days}d</span>
                <span className="ward-stat-label">Avg Resolution Time</span>
              </div>
              <div className="ward-stat-card">
                <span className="ward-stat-value">{wardStats.top_categories.length}</span>
                <span className="ward-stat-label">Categories</span>
              </div>
              {wardStats.top_categories.length > 0 && (
                <div className="ward-categories-card">
                  <span className="ward-stat-label">Top Categories</span>
                  <div className="ward-categories-list">
                    {wardStats.top_categories.slice(0, 5).map((c, i) => (
                      <div key={i} className="ward-category-row">
                        <span className="ward-cat-name">{c.category}</span>
                        <span className="ward-cat-count">{c.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
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

        <div className="chart-grid chart-grid-2">
          <div className="chart-card">
            <div className="chart-hdr">
              <h3>{t('transparency.hourChartTitle')}</h3>
              <span className="chart-desc">{t('transparency.hourChartSubtitle')}</span>
            </div>
            {(!data?.complaintsByHour || data.complaintsByHour.length === 0) ? (
              <p className="empty-chart">{t('transparency.noData')}</p>
            ) : (
              <Plot
                data={[{
                  x: data.complaintsByHour.map(h => h.hour),
                  y: data.complaintsByHour.map(h => h.count),
                  type: 'bar',
                  marker: { color: '#3b82f6' },
                }]}
                layout={{
                  autosize: true, height: 200,
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#94a3b8', size: 10 },
                  margin: { t: 10, b: 30, l: 30, r: 10 },
                  xaxis: {
                    tickmode: 'array',
                    tickvals: [0, 3, 6, 9, 12, 15, 18, 21],
                    ticktext: ['Midnight', '3 AM', '6 AM', '9 AM', 'Noon', '3 PM', '6 PM', '9 PM'],
                    gridcolor: 'rgba(255,255,255,0.05)', zeroline: false,
                  },
                  yaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false },
                  bargap: 0.2,
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            )}
          </div>

          <div className="chart-card">
            <div className="chart-hdr">
              <h3>{t('transparency.dayChartTitle')}</h3>
              <span className="chart-desc">{t('transparency.dayChartSubtitle')}</span>
            </div>
            {(!data?.complaintsByDay || data.complaintsByDay.length === 0) ? (
              <p className="empty-chart">{t('transparency.noData')}</p>
            ) : (
              <Plot
                data={[{
                  x: data.complaintsByDay.map(d => d.day),
                  y: data.complaintsByDay.map(d => d.count),
                  type: 'bar',
                  marker: { color: '#8b5cf6' },
                }]}
                layout={{
                  autosize: true, height: 200,
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#94a3b8', size: 10 },
                  margin: { t: 10, b: 30, l: 30, r: 10 },
                  xaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false },
                  yaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false },
                  bargap: 0.3,
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            )}
          </div>
        </div>

        {wordCloud.length > 0 && (() => {
          const maxCount = Math.max(...wordCloud.map((w: any) => w.count));
          return (
            <div className="word-cloud-section">
              <h3>Common Complaint Keywords</h3>
              <div className="word-cloud">
                {wordCloud.map((w: any) => (
                  <span key={w.word} className="word-cloud-tag" style={{ fontSize: `${Math.max(0.7, Math.min(2.5, w.count / maxCount * 2.5))}rem`, opacity: `${0.5 + (w.count / maxCount) * 0.5}` }}>
                    {w.word}
                  </span>
                ))}
              </div>
            </div>
          );
        })()}

        {stories.length > 0 && (
          <div className="success-stories-section">
            <div className="section-header">
              <h2><Star size={20} /> {t('transparency.successStoriesTitle')}</h2>
              <p>{t('transparency.successStoriesSubtitle')}</p>
            </div>
            <div className="stories-grid">
              {stories.map((s, i) => (
                <div key={i} className="story-card">
                  <div className="story-header">
                    <span className="story-category">{s.category}</span>
                    <span className="story-rating">
                      {[1, 2, 3, 4, 5].map(n => (
                        <Star key={n} size={14} className={n <= s.citizen_rating ? 'star-filled' : 'star-empty'} />
                      ))}
                    </span>
                  </div>
                  <div className="story-meta">
                    <span><MapPin size={12} /> Ward {s.ward}</span>
                    <span><Building2 size={12} /> {s.department}</span>
                    <span><Clock size={12} /> Resolved in {s.days_to_resolve}d</span>
                  </div>
                  {s.resolution_note && <p className="story-note">"{s.resolution_note}"</p>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Transparency;
