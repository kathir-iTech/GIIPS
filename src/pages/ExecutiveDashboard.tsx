import React, { useEffect, useState, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import Header from '../components/Header';
import KPICard from '../components/KPICard';
import { AgingBadge } from '../components/AgingBadge';
import { getDeptI18nKey, getDeptIconKeyword } from '../data/departments';
import {
  AlertOctagon, TrendingUp, ShieldAlert, Building2, Zap, Activity, Users, Clock,
  MapPin, BarChart3, RefreshCw, Download, Share2, ArrowUpRight, ArrowDownRight,
  Minus, ChevronRight, Wrench, Droplets, Lightbulb, Trash2, Heart,
  Road, Send, Loader2, Brain, Target, Compass, AlertTriangle, CheckCircle2,
  DollarSign, Calendar, Gauge, Sparkles, Bot, MessageSquare, Flame, ThermometerSun,
  Users2, ArrowRight
} from 'lucide-react';
import './ExecutiveDashboard.css';

const EXEC_DEPT_COLORS: Record<string, string> = {
  roads: '#ef4444',
  water: '#3b82f6',
  drainage: '#10b981',
  electricity: '#eab308',
  streetlight: '#f59e0b',
  garbage: '#8b5cf6',
  health: '#06b6d4',
  traffic: '#f97316',
  fire: '#dc2626',
};

const SkeletonCard: React.FC = () => (
  <div className="skeleton-card">
    <div className="skeleton-header" />
    <div className="skeleton-value" />
    <div className="skeleton-subtitle" />
  </div>
);

const buildSparklinePath = (data: number[], width: number, height: number): string => {
  if (!data || data.length < 2) return '';
  const max = Math.max(...data, 1);
  const pad = 2;
  const h = height - pad * 2;
  return data.map((v, i) => {
    const x = (i / (data.length - 1)) * (width - pad * 2) + pad;
    const y = h - ((v / max) * h) + pad;
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
};

const Sparkline: React.FC<{ data?: number[]; color?: string; trend?: 'up' | 'down' | 'flat' }> = ({ data = [], color = '#3b82f6', trend = 'up' }) => (
  <svg width="80" height="30" viewBox="0 0 80 30" className="kpi-sparkline">
    <path d={buildSparklinePath(data, 80, 30)} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    {trend === 'up' && <ArrowUpRight size={12} className="spark-trend spark-up" />}
    {trend === 'down' && <ArrowDownRight size={12} className="spark-trend spark-down" />}
    {trend === 'flat' && <Minus size={12} className="spark-trend spark-flat" />}
  </svg>
);

const SectionCard: React.FC<{ title: string; subtitle?: string; icon?: React.ReactNode; children: React.ReactNode; className?: string }> = ({
  title, subtitle, icon, children, className = ''
}) => {
  const { t } = useTranslation();
  return (
    <div className={`section-card glass-card ${className}`}>
      <div className="card-header">
        <div className="card-title-group">
          {icon && <span className="card-icon">{icon}</span>}
          <div>
            <h3>{title}</h3>
            {subtitle && <span className="card-subtitle">{subtitle}</span>}
          </div>
        </div>
        <div className="card-actions">
          <button className="icon-btn" title={t('common.tooltip.refresh')}><RefreshCw size={14} /></button>
          <button className="icon-btn" title={t('common.tooltip.download')}><Download size={14} /></button>
          <button className="icon-btn" title={t('common.tooltip.share')}><Share2 size={14} /></button>
        </div>
      </div>
      <div className="card-body">
        {children}
      </div>
    </div>
  );
};

const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const { t } = useTranslation();
  const color = priority?.toLowerCase() === 'critical' ? '#dc2626'
    : priority?.toLowerCase() === 'high' ? '#ea580c'
    : priority?.toLowerCase() === 'medium' ? '#ca8a04'
    : '#16a34a';
  return <span className="priority-badge" style={{ backgroundColor: `${color}18`, color, border: `1px solid ${color}40` }}>{t(`common.priority.${priority?.toLowerCase()}`)}</span>;
};

const TrendIndicator: React.FC<{ value: number }> = ({ value }) => {
  if (value > 0) return <span className="trend-up"><ArrowUpRight size={14} />{Math.abs(value)}%</span>;
  if (value < 0) return <span className="trend-down"><ArrowDownRight size={14} />{Math.abs(value)}%</span>;
  return <span className="trend-flat"><Minus size={14} />0%</span>;
};

const ExecutiveDashboard = () => {
  const { t, i18n } = useTranslation();
  const dateLocale = i18n.language === 'ta' ? 'ta-IN' : 'en-IN';
  const chatEndRef = useRef<HTMLDivElement>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [execSummary, setExecSummary] = useState<any>(null);
  const [wardHealth, setWardHealth] = useState<any[]>([]);
  const [deptWorkload, setDeptWorkload] = useState<any[]>([]);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [predictions, setPredictions] = useState<any>(null);
  const [knowledge, setKnowledge] = useState<any>(null);
  const [decisionSupport, setDecisionSupport] = useState<any>(null);
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [timelineDays, setTimelineDays] = useState<number>(30);
  const [escalating, setEscalating] = useState(false);

  const [trendLabels, setTrendLabels] = useState<string[]>([]);
  const [trendComplaints, setTrendComplaints] = useState<number[]>([]);

  const [copilotMessages, setCopilotMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [copilotInput, setCopilotInput] = useState('');
  const [copilotLoading, setCopilotLoading] = useState(false);
  useEffect(() => {
    let mounted = true;

    const fetchAll = async (showLoader = false) => {
      if (!mounted) return;
      if (showLoader) setLoading(true);
      try {
        const results = await Promise.allSettled([
          api.getExecutiveSummary(),
          api.getWardHealth(),
          api.getDeptWorkload(),
          api.getIncidents(undefined, 2000),
          api.getPredictionsSummary(),
          api.getKnowledgeSummary(),
          api.getDecisionSupportSummary(),
          api.getSystemHealth().catch(() => ({})),
          fetch(`${import.meta.env.VITE_API_BASE_URL}/dashboard/trend`).then(r => r.json()).catch(() => ({ labels: [], complaints: [], incidents: [] })),
        ]);
        if (!mounted) return;
        const feedErrors: string[] = [];
        const checkFeed = (r: any, name: string) => {
          if (r.status === 'rejected') {
            feedErrors.push(`${name} (${r.reason?.message || 'unknown error'})`);
            return null;
          }
          return r.value;
        };
        setExecSummary(checkFeed(results[0], 'execSummary'));
        setWardHealth(checkFeed(results[1], 'wardHealth') || []);
        setDeptWorkload(checkFeed(results[2], 'deptWorkload') || []);
        setIncidents(checkFeed(results[3], 'incidents') || []);
        setPredictions(checkFeed(results[4], 'predictions'));
        setKnowledge(checkFeed(results[5], 'knowledge'));
        setDecisionSupport(checkFeed(results[6], 'decisionSupport'));
        setSystemHealth(checkFeed(results[7], 'systemHealth'));
        const trendRaw = checkFeed(results[8], 'trend');
        if (trendRaw && trendRaw.labels) {
          setTrendLabels(trendRaw.labels || []);
          setTrendComplaints(trendRaw.complaints || []);
        }
        if (feedErrors.length > 0) {
          const msg = t('executive.feedErrors.someOffline') + feedErrors.join('; ');
          console.error(msg);
          if (showLoader) setError(msg);
        }
      } catch (err) {
        if (!mounted) return;
        if (showLoader) {
          console.error('Failed to fetch executive dashboard data:', err);
          setError(t('executive.global.feedOffline'));
        }
      } finally {
        if (showLoader && mounted) setLoading(false);
      }
    };

    fetchAll(true);
    const interval = setInterval(() => fetchAll(false), 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  useEffect(() => {
    if (chatEndRef.current) chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [copilotMessages]);

  const handleCopilotSend = async (overrideMessage?: string) => {
    const msg = overrideMessage || copilotInput.trim();
    if (!msg) return;
    setCopilotMessages(prev => [...prev, { role: 'user', content: msg }]);
    setCopilotInput('');
    setCopilotLoading(true);
    try {
      const history = copilotMessages.map(m => ({ role: m.role, content: m.content }));
      const res = await api.copilotChat(msg, history);
      const reply = res.response || res.message || res.reply || t('common.copilot.processing');
      setCopilotMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch {
      setCopilotMessages(prev => [...prev, { role: 'assistant', content: t('common.copilot.error') }]);
    } finally {
      setCopilotLoading(false);
    }
  };

  const criticalIncidents = useMemo(() => incidents.filter((i: any) => i.priority_label?.toLowerCase() === 'critical').slice(0, 5), [incidents]);
  const highIncidents = useMemo(() => incidents.filter((i: any) => i.priority_label?.toLowerCase() === 'high').slice(0, 10), [incidents]);
  const agingCount = useMemo(() => incidents.filter((i: any) => (i.days_open ?? 0) >= 30).length, [incidents]);
  const topDistricts = useMemo(() => [...(wardHealth || [])].sort((a: any, b: any) => (b.healthScore || 0) - (a.healthScore || 0)).slice(0, 5), [wardHealth]);
  const criticalDistricts = useMemo(() => [...(wardHealth || [])].sort((a: any, b: any) => (a.healthScore || 0) - (b.healthScore || 0)).slice(0, 5), [wardHealth]);

  const totalComplaints = execSummary?.totalComplaints ?? execSummary?.todayComplaints ?? 0;
  const criticalCount = execSummary?.criticalIncidentCount ?? execSummary?.criticalIncidents ?? 0;
  const resolutionTime = execSummary?.avgResolutionTime ?? execSummary?.avg_days_open ?? 2.4;

  const complaintTrend = useMemo(() => {
    if (trendComplaints.length < 2) return 0;
    const first = trendComplaints[0];
    const last = trendComplaints[trendComplaints.length - 1];
    if (first === 0) return 0;
    return Math.round(((last - first) / first) * 100);
  }, [trendComplaints]);

  const criticalTrend = useMemo(() => {
    const prior = execSummary?.priorCriticalIncidents;
    const curr = criticalCount;
    if (prior == null || prior === 0) return 0;
    return Math.round(((curr - prior) / prior) * 100);
  }, [execSummary, criticalCount]);

  const resolutionTrend = useMemo(() => {
    const prior = execSummary?.priorAvgResolutionTime;
    if (prior == null || prior === 0) return 0;
    return Math.round(((resolutionTime - prior) / prior) * 100);
  }, [execSummary, resolutionTime]);

  if (loading) {
    return (
      <div className="exec-dashboard">
        <Header title={t('executive.header.title')} subtitle={t('executive.header.loadingSubtitle')} />
        <section className="kpi-skeleton-grid">
          {Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)}
        </section>
        <div className="main-grid-skeleton">
          <div className="skeleton-panel"><div className="skeleton-card tall" /></div>
          <div className="skeleton-panel"><div className="skeleton-card" /><div className="skeleton-card" /></div>
        </div>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>{t('executive.loading.syncing')}</p>
        </div>
      </div>
    );
  }

  if (!execSummary) {
    return (
      <div className="exec-dashboard">
        <Header title={t('executive.header.title')} subtitle={t('executive.header.errorSubtitle')} />
        <div className="error-state">
          <AlertTriangle size={48} />
          <h2>{t('executive.error.title')}</h2>
          <p>{error || t('executive.error.body')}</p>
          <button className="retry-btn" onClick={() => window.location.reload()}>{t('executive.error.retry')}</button>
        </div>
      </div>
    );
  }

  const recommendations = decisionSupport?.recommendations || decisionSupport?.actions || [];
  const districtsAtRisk = wardHealth?.filter((w: any) => (w.healthScore || 100) < 60) || [];

  const copilotSuggestions: string[] = [];

  const autoEscalate = async () => {
    setEscalating(true);
    try {
      const result = await api.autoEscalateIncidents();
      alert(result.message || 'Auto-escalation complete');
    } catch (err: any) {
      alert(err.message || 'Auto-escalation failed');
    } finally {
      setEscalating(false);
    }
  };

  return (
    <div className="exec-dashboard">
      <Header title={t('executive.header.title')} subtitle={t('executive.header.subtitle')} />

      {error && <div className="global-banner warning"><AlertTriangle size={16} />{error}</div>}

      <div className="exec-toolbar">
        <button className="action-btn escalate-btn" onClick={autoEscalate} disabled={escalating}>
          {escalating ? <Loader2 size={14} className="spin" /> : <Zap size={14} />}
          Run SLA Auto-Escalation Check
        </button>
      </div>

      {/* 1. Government Situation Summary */}
      <SectionCard title={t('executive.situation.title')} subtitle={t('executive.situation.subtitle')} icon={<Gauge size={18} />}>
        <div className="kpi-scroll-grid">
          <div className="kpi-item">
            <div className="kpi-icon-wrapper complaints"><MessageSquare size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">{t('executive.kpi.todayComplaints')}</span>
              <span className="kpi-value">{totalComplaints}</span>
              <TrendIndicator value={complaintTrend} />
            </div>
            <Sparkline data={trendComplaints} color="#3b82f6" trend={complaintTrend > 0 ? 'up' : complaintTrend < 0 ? 'down' : 'flat'} />
          </div>
          <div className="kpi-item critical">
            <div className="kpi-icon-wrapper critical"><AlertOctagon size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">{t('executive.kpi.criticalIncidents')}</span>
              <span className="kpi-value">{criticalCount}</span>
              <TrendIndicator value={criticalTrend} />
            </div>
            <Sparkline color="#dc2626" trend={criticalTrend > 0 ? 'up' : criticalTrend < 0 ? 'down' : 'flat'} />
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper districts"><MapPin size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">{t('executive.kpi.districtsAtRisk')}</span>
              <span className="kpi-value">{districtsAtRisk.length}</span>
            </div>
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper stress"><ThermometerSun size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">{t('executive.kpi.deptsUnderStress')}</span>
              <span className="kpi-value">{(deptWorkload || []).filter((d: any) => (d.stressLevel || d.efficiency || 100) < 60).length}</span>
            </div>
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper escalation"><Flame size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">{t('executive.kpi.predictedEscalations')}</span>
              <span className="kpi-value">{predictions?.predictedEscalations ?? predictions?.escalations ?? 7}</span>
            </div>
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper resolution"><Clock size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">{t('executive.kpi.avgResolutionTime')}</span>
              <span className="kpi-value">{resolutionTime?.toFixed?.(1) ?? resolutionTime}{t('common.time.days')}</span>
              <TrendIndicator value={resolutionTrend} />
            </div>
            <Sparkline color="#22c55e" trend={resolutionTrend < 0 ? 'down' : resolutionTrend > 0 ? 'up' : 'flat'} />
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper weekly"><Activity size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">{t('executive.kpi.weeklyTrend')}</span>
              <span className="kpi-value">{t('executive.kpi.stable')}</span>
              <TrendIndicator value={complaintTrend} />
            </div>
            <Sparkline data={trendComplaints} color="#10b981" trend={complaintTrend > 0 ? 'up' : complaintTrend < 0 ? 'down' : 'flat'} />
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper system"><ServerIcon size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">{t('executive.kpi.systemHealth')}</span>
              <span className="kpi-value">{systemHealth?.backend === 'healthy' ? t('executive.kpi.optimal') : t('executive.kpi.stable')}</span>
              <TrendIndicator value={0} />
            </div>
            <Sparkline color="#06b6d4" trend="flat" />
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper aging"><Clock size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">Aging &gt;30d</span>
              <span className="kpi-value" style={agingCount > 0 ? { color: '#9333ea' } : undefined}>{agingCount}</span>
            </div>
          </div>
        </div>
      </SectionCard>

      {/* 2. AI Executive Brief */}
      <SectionCard title={t('executive.brief.title')} subtitle={t('executive.brief.subtitle')} icon={<Brain size={18} />}>
        <div className="executive-brief">
          <div className="brief-header">
            <div className="brief-badge ai"><Sparkles size={14} /> {t('executive.brief.aiGenerated')}</div>
            <div className="brief-confidence">
              <span className="confidence-label">{t('executive.brief.confidence')}</span>
              <span className="confidence-value">{(decisionSupport?.confidence ?? predictions?.confidence ?? 88).toFixed(0)}%</span>
              <div className="confidence-bar"><div className="confidence-fill" style={{ width: `${(decisionSupport?.confidence ?? predictions?.confidence ?? 88)}%` }} /></div>
            </div>
          </div>
          {(decisionSupport?.executiveSummary || decisionSupport?.summary || knowledge?.summary || predictions?.summary) ? (
            <p className="brief-text">{decisionSupport?.executiveSummary || decisionSupport?.summary || knowledge?.summary || predictions?.summary}</p>
          ) : (
            <div className="empty-chart"><Brain size={32} /><p>{t('executive.brief.empty')}</p></div>
          )}
          <div className="brief-footer">
            <span className="brief-time">{t('executive.brief.generated')} {new Date().toLocaleString(dateLocale, { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' })}</span>
            <div className="brief-engines">
              {(() => {
                const engines: { key: string; label: string }[] = [];
                if (predictions) engines.push({ key: 'prediction', label: t('common.engineTags.prediction') });
                if (decisionSupport) engines.push({ key: 'decision', label: t('common.engineTags.decision') });
                if (knowledge) engines.push({ key: 'knowledge', label: t('common.engineTags.knowledge') });
                return engines.length > 0
                  ? engines.map(eng => <span key={eng.key} className="engine-tag">{eng.label}</span>)
                  : <span className="engine-tag">{t('common.engineTags.prediction')}</span>;
              })()}
            </div>
          </div>
        </div>
      </SectionCard>

      {/* 3. AI Recommended Government Actions */}
      <SectionCard title={t('executive.actions.title')} subtitle={t('executive.actions.subtitle')} icon={<Target size={18} />}>
        {recommendations.length > 0 ? (
          <div className="recommendations-grid">
            {recommendations.slice(0, 6).map((rec: any, idx: number) => (
              <div key={idx} className={`rec-card priority-${(rec.priority || rec.severity || 'medium').toLowerCase()}`}>
                <div className="rec-top">
                  <span className="rec-number">#{idx + 1}</span>
                  <PriorityBadge priority={rec.priority || rec.severity || 'Medium'} />
                </div>
                <h4>{rec.title || rec.action || rec.recommendation || t('executive.actions.fallbackTitle')}</h4>
                <p className="rec-reason">{rec.reason || t('executive.actions.fallbackReason')}</p>
                <div className="rec-metrics">
                  <div className="rec-metric">
                    <span className="rec-metric-label">{t('executive.actions.expectedImpact')}</span>
                    <span className="rec-metric-value positive">{rec.expectedImpact ?? rec.expected_improvement ?? rec.impact ?? '15%'} {t('common.time.improvement')}</span>
                  </div>
                  <div className="rec-metric">
                    <span className="rec-metric-label">{t('executive.actions.department')}</span>
                    <span className="rec-metric-value">{rec.department || rec.responsibleDept || 'Infrastructure'}</span>
                  </div>
                </div>
                <div className="rec-footer">
                  <div className="rec-chips">
                    {rec.affectedPopulation && <span className="rec-chip"><Users2 size={12} /> {(rec.affectedPopulation || 0).toLocaleString()} {t('common.time.affected')}</span>}
                    {rec.confidence && <span className="rec-chip"><Activity size={12} /> {rec.confidence}% {t('common.time.confidence')}</span>}
                  </div>
                  <button className="rec-action-btn">{t('executive.actions.deploy')} <ArrowRight size={14} /></button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <CheckCircle2 size={32} />
            <p>{t('executive.actions.empty')}</p>
          </div>
        )}
      </SectionCard>

      {/* 4. District Intelligence */}
      <SectionCard title={t('executive.district.title')} subtitle={t('executive.district.subtitle')} icon={<Compass size={18} />}>
        <div className="district-grid">
          <div className="district-panel">
            <h4><TrendingUp size={14} /> {t('executive.district.topPerforming')}</h4>
            {topDistricts.map((d: any, i: number) => (
              <div key={i} className="district-row top">
                <span className="district-rank">#{i + 1}</span>
                <span className="district-name">{d.ward || d.district || d.name || `Ward ${i + 1}`}</span>
                <span className="district-score good">{(d.healthScore || d.score || 85) + '%'}</span>
              </div>
            ))}
          </div>
          <div className="district-panel critical-panel">
            <h4><AlertTriangle size={14} /> {t('executive.district.mostCritical')}</h4>
            {criticalDistricts.map((d: any, i: number) => (
              <div key={i} className="district-row critical">
                <span className="district-rank">#{i + 1}</span>
                <span className="district-name">{d.ward || d.district || d.name || `Ward ${i + 1}`}</span>
                <span className="district-score bad">{(d.healthScore || d.score || 35) + '%'}</span>
              </div>
            ))}
          </div>
          <div className="district-panel">
            <h4><Zap size={14} /> {t('executive.district.fastestImproving')}</h4>
            {topDistricts.slice().reverse().slice(0, 3).map((d: any, i: number) => (
              <div key={i} className="district-row improving">
                <span className="district-rank">#{i + 1}</span>
                <span className="district-name">{d.ward || d.district || d.name || `Ward ${i + 3}`}</span>
                <span className="district-score good">+{(d.trend || d.improvement || 12)}%</span>
              </div>
            ))}
          </div>
          <div className="district-panel warning-panel">
            <h4><Flame size={14} /> {t('executive.district.highestGrowth')}</h4>
            {criticalDistricts.slice(0, 3).map((d: any, i: number) => (
              <div key={i} className="district-row growth">
                <span className="district-rank">#{i + 1}</span>
                <span className="district-name">{d.ward || d.district || d.name || `Ward ${i + 5}`}</span>
                <span className="district-score bad">+{(d.growth || d.complaintGrowth || 28)}%</span>
              </div>
            ))}
          </div>
        </div>
      </SectionCard>

      {/* 5. Department Performance */}
      <SectionCard title={t('executive.dept.title')} subtitle={t('executive.dept.subtitle')} icon={<BarChart3 size={18} />}>
        <div className="dept-grid">
          {(deptWorkload && deptWorkload.length > 0 ? deptWorkload : []).map((dept: any, idx: number) => {
            const name = dept.department || dept.name || '';
            const efficiency = dept.efficiency ?? dept.score ?? 70;
            const iconKey = getDeptIconKeyword(name);
            const deptIcon = iconKey === 'road' ? Road : iconKey === 'water' ? Droplets : iconKey === 'electricity' ? Zap : iconKey === 'streetlight' ? Lightbulb : iconKey === 'garbage' ? Trash2 : iconKey === 'health' ? Heart : iconKey === 'traffic' ? AlertOctagon : iconKey === 'fire' ? Flame : Wrench;
            const color = EXEC_DEPT_COLORS[iconKey] || '#64748b';
            return (
              <div key={idx} className="dept-card" style={{ borderLeftColor: color }}>
                <div className="dept-header">
                  <div className="dept-icon" style={{ color, background: `${color}18` }}>{React.createElement(deptIcon, { size: 18 })}</div>
                  <div>
                    <h4>{t(getDeptI18nKey(name))}</h4>
                    <span className="dept-status" style={{ color }}>{efficiency > 75 ? t('common.deptStatus.healthy') : efficiency > 55 ? t('common.deptStatus.stressed') : t('common.deptStatus.underStress')}</span>
                  </div>
                </div>
                <div className="dept-rings">
                  <div className="dept-ring">
                    <svg viewBox="0 0 36 36">
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e2e8f0" strokeWidth="3" />
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke={color} strokeWidth="3" strokeDasharray={`${efficiency}, 100`} strokeLinecap="round" />
                      <text x="18" y="20.35" textAnchor="middle" fontSize="8" fontWeight="700" fill={color}>{efficiency}%</text>
                    </svg>
                    <span>{t('executive.dept.efficiency')}</span>
                  </div>
                  <div className="dept-ring">
                    <svg viewBox="0 0 36 36">
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e2e8f0" strokeWidth="3" />
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke={color} strokeWidth="3" strokeDasharray={`${100 - (dept.criticalPercent ?? 20)}, 100`} strokeLinecap="round" />
                      <text x="18" y="20.35" textAnchor="middle" fontSize="8" fontWeight="700" fill={color}>{100 - (dept.criticalPercent ?? 20)}%</text>
                    </svg>
                    <span>{t('executive.dept.safety')}</span>
                  </div>
                </div>
                <div className="dept-stats">
                  <div className="dept-stat"><span className="dept-stat-label">{t('executive.dept.openIncidents')}</span><span className="dept-stat-value">{dept.activeIncidents ?? dept.openIncidents ?? 0}</span></div>
                  <div className="dept-stat"><span className="dept-stat-label">{t('executive.dept.criticalPercent')}</span><span className="dept-stat-value bad">{dept.criticalPercent ?? dept.critical ?? 0}%</span></div>
                  <div className="dept-stat"><span className="dept-stat-label">{t('executive.dept.avgResolution')}</span><span className="dept-stat-value">{(dept.avgResolution ?? 2.5).toFixed(1)}{t('common.time.days')}</span></div>
                </div>
                {dept.recommendation && <p className="dept-recommendation">{dept.recommendation}</p>}
              </div>
            );
          })}
          {(!deptWorkload || deptWorkload.length === 0) && (
            <div className="empty-chart"><BarChart3 size={32} /><p>{t('executive.dept.empty')}</p></div>
          )}
        </div>
      </SectionCard>

      {/* 6. Emerging Risks */}
      <SectionCard title={t('executive.risks.title')} subtitle={t('executive.risks.subtitle')} icon={<Flame size={18} />}>
        <div className="risks-grid">
          {((predictions?.risks || predictions?.emergingRisks || []) || []).map((risk: any, idx: number) => (
            <div key={idx} className={`risk-card risk-${(risk.severity || risk.priority || 'medium').toLowerCase()}`}>
              <div className="risk-header">
                <h4>{risk.category || risk.title || t('executive.risks.fallbackCategory')}</h4>
                <PriorityBadge priority={risk.severity || risk.priority || 'Medium'} />
              </div>
              <p className="risk-reason">{risk.reason || risk.description || t('executive.risks.fallbackReason')}</p>
              <div className="risk-meta">
                <span className="risk-confidence"><Activity size={12} /> {risk.confidence ?? risk.confidence_score ?? 75}% {t('executive.risks.confidence')}</span>
                {risk.suggestion && <span className="risk-suggestion"><Target size={12} /> {risk.suggestion}</span>}
              </div>
            </div>
          ))}
          {(!predictions?.risks?.length && !predictions?.emergingRisks?.length) && (
            <div className="empty-chart"><Flame size={32} /><p>{t('executive.risks.empty')}</p></div>
          )}
        </div>
      </SectionCard>

      {/* 7. Incident Command Center */}
      <SectionCard title={t('executive.incidents.title')} subtitle={t('executive.incidents.subtitle', { criticalCount: criticalIncidents.length })} icon={<ShieldAlert size={18} />}>
        <div className="incidents-command">
          {criticalIncidents.length > 0 ? criticalIncidents.map((inc: any) => (
            <div key={inc.id} className="incident-command-card">
              <div className="inc-command-top">
                <span className="inc-number">{inc.incident_number}</span>
                <PriorityBadge priority={inc.priority_label} />
                <span className="inc-ward"><MapPin size={12} />{inc.ward}</span>
              </div>
              <p className="inc-summary">{inc.summary}</p>
              <div className="inc-command-bottom">
                <div className="inc-meta">
                  <span className="inc-cluster"><Users size={12} /> {inc.cluster_size || 1} {t('executive.incidents.reports')}</span>
                  <span className="inc-days"><Clock size={12} /> <AgingBadge daysOpen={inc.days_open || 0} /></span>
                </div>
                <div className="inc-action">
                  <span className="inc-recommendation">{inc.recommended_action}</span>
                  <button className="inc-detail-btn" onClick={() => window.location.href = `/incident-feed`}>{t('executive.incidents.openDetail')} <ChevronRight size={14} /></button>
                </div>
              </div>
            </div>
          )) : (
            <div className="empty-state">
              <CheckCircle2 size={32} />
              <p>{t('executive.incidents.empty')}</p>
            </div>
          )}
        </div>
      </SectionCard>

      {/* 8. AI Copilot */}
      <SectionCard title={t('executive.copilot.title')} subtitle={t('executive.copilot.subtitle')} icon={<Bot size={18} />}>
        <div className="copilot-panel">
          <div className="copilot-messages">
            {copilotMessages.map((msg, idx) => (
              <div key={idx} className={`copilot-msg ${msg.role}`}>
                <div className="msg-avatar">
                  {msg.role === 'assistant' ? <Bot size={16} /> : <Users2 size={16} />}
                </div>
                <div className="msg-bubble">
                  <p>{msg.content}</p>
                </div>
              </div>
            ))}
            {copilotLoading && (
              <div className="copilot-msg assistant">
                <div className="msg-avatar"><Bot size={16} /></div>
                <div className="msg-bubble typing">
                  <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
          {copilotMessages.length <= 1 && (
            <div className="copilot-suggestions">
              {copilotSuggestions.map(s => (
                <button key={s} className="suggestion-chip" onClick={() => handleCopilotSend(s)}>{s}</button>
              ))}
            </div>
          )}
          <div className="copilot-input-row">
            <input
              type="text"
              value={copilotInput}
              onChange={e => setCopilotInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCopilotSend()}
              placeholder={t('common.copilot.placeholder')}
              disabled={copilotLoading}
            />
            <button className="send-btn" onClick={() => handleCopilotSend()} disabled={copilotLoading || !copilotInput.trim()}>
              {copilotLoading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
            </button>
          </div>
        </div>
      </SectionCard>

      {/* 9. Resource Allocation */}
      <SectionCard title={t('executive.resources.title')} subtitle={t('executive.resources.subtitle')} icon={<Users size={18} />}>
        <div className="resource-grid">
          {(decisionSupport?.resourceAllocation || decisionSupport?.resources || []).map((res: any, idx: number) => (
            <div key={idx} className="resource-card">
              <div className="resource-header">
                <h4>{res.department || res.name || 'General'}</h4>
                <span className="resource-improvement positive">+{res.improvement ?? res.improvement_percent ?? 20}% {t('executive.resources.improvement')}</span>
              </div>
              <div className="resource-bars">
                <div className="resource-bar-group">
                  <div className="resource-bar-label"><Users size={12} /> {t('executive.resources.current')} <strong>{res.current ?? res.current_teams ?? 5}</strong></div>
                  <div className="resource-bar-track"><div className="resource-bar-fill current" style={{ width: `${((res.current ?? res.current_teams ?? 5) / 15) * 100}%` }} /></div>
                </div>
                <ArrowRight size={16} className="resource-arrow" />
                <div className="resource-bar-group">
                  <div className="resource-bar-label"><Target size={12} /> {t('executive.resources.recommended')} <strong>{res.recommended ?? res.recommended_teams ?? 8}</strong></div>
                  <div className="resource-bar-track"><div className="resource-bar-fill recommended" style={{ width: `${((res.recommended ?? res.recommended_teams ?? 8) / 15) * 100}%` }} /></div>
                </div>
              </div>
              <div className="resource-stats">
                <span className="resource-stat"><DollarSign size={12} /> {res.costReduction ?? res.cost_saving ?? 12}% {t('executive.resources.costReduction')}</span>
                <span className="resource-stat"><Activity size={12} /> {res.gain ?? res.expectedResolutionGain ?? `+150 ${t('common.time.faster')}`}</span>
              </div>
            </div>
          ))}
          {(!decisionSupport?.resourceAllocation?.length && !decisionSupport?.resources?.length) && (
            <div className="empty-chart"><Users size={32} /><p>{t('executive.resources.empty')}</p></div>
          )}
        </div>
      </SectionCard>

      {/* 10. Predictive Timeline */}
      <SectionCard title={t('executive.timeline.title')} subtitle={t('executive.timeline.subtitle')} icon={<Calendar size={18} />}>
        <div className="timeline-tabs">
          {[7, 15, 30].map(days => (
            <button key={days} className={`timeline-tab ${timelineDays === days ? 'active' : ''}`} onClick={() => setTimelineDays(days)}>{days} {t('executive.timeline.days')}</button>
          ))}
        </div>
        {predictions ? (
          <div className="timeline-chart">
            <Plot
              data={[
                {
                  x: Array.from({ length: timelineDays }, (_, i) => `${t('executive.timeline.day')} ${i + 1}`),
                  y: Array.from({ length: timelineDays }, (_, i) =>
                    predictions.predicted_volume
                      ? Math.round(predictions.predicted_volume * (0.8 + (i / timelineDays) * 0.4))
                      : 0
                  ),
                  type: 'scatter',
                  mode: 'lines+markers',
                  name: t('executive.timeline.predictedVolume'),
                  line: { color: '#3b82f6', width: 3, shape: 'spline' },
                  marker: { size: 6, color: '#3b82f6' },
                  fill: 'tozeroy',
                  fillcolor: 'rgba(59,130,246,0.1)',
                },
              ]}
              layout={{
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                height: 320,
                margin: { t: 20, b: 40, l: 40, r: 20 },
                legend: { orientation: 'h', y: -0.15, x: 0.5, xanchor: 'center' },
                xaxis: { showgrid: false, color: '#94a3b8', tickfont: { size: 11 } },
                yaxis: { showgrid: true, gridcolor: 'rgba(0,0,0,0.05)', color: '#94a3b8', tickfont: { size: 11 } },
              }}
              style={{ width: '100%' }}
              config={{ displayModeBar: false, responsive: true }}
            />
          </div>
        ) : (
          <div className="empty-chart">
            <Calendar size={32} />
            <p>{t('executive.timeline.empty')}</p>
          </div>
        )}
      </SectionCard>

      <footer className="exec-footer">
        <span>{t('executive.footer.title')}</span>
        <span>{t('executive.footer.dataRefreshed')} {new Date().toLocaleString(dateLocale)}</span>
      </footer>
    </div>
  );
};

const ServerIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2" /><rect x="2" y="14" width="20" height="8" rx="2" ry="2" /><line x1="6" y1="6" x2="6.01" y2="6" /><line x1="6" y1="18" x2="6.01" y2="18" /></svg>
);

export default ExecutiveDashboard;
