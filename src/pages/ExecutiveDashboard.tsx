import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import { useDashboardSocket } from '../hooks/useDashboardSocket';
import Header from '../components/Header';
import KPICard from '../components/KPICard';
import { AgingBadge } from '../components/AgingBadge';
import { getDeptI18nKey, getDeptIconKeyword } from '../data/departments';
import { getCoimbatoreZone } from '../data/coimbatoreZones';
import {
  AlertOctagon, TrendingUp, ShieldAlert, Building2, Zap, Activity, Users, Clock,
  MapPin, BarChart3, RefreshCw, Download, Share2, ArrowUpRight, ArrowDownRight,
  Minus, ChevronRight, ChevronDown, Wrench, Droplets, Lightbulb, Trash2, Heart,
  Road, Send, Loader2, Brain, Target, Compass, AlertTriangle, CheckCircle2,
  DollarSign, Calendar, Gauge, Sparkles, Bot, MessageSquare, Flame, ThermometerSun,
  Users2, ArrowRight, FileText, Layers
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

const SectionCard: React.FC<{ title: string; subtitle?: string; icon?: React.ReactNode; children: React.ReactNode; className?: string; badge?: string }> = ({
  title, subtitle, icon, children, className = '', badge
}) => {
  const { t } = useTranslation();
  return (
    <div className={`section-card glass-card ${className}`}>
      <div className="card-header">
        <div className="card-title-group">
          {icon && <span className="card-icon">{icon}</span>}
          <div>
            <h3>{title}{badge && <span className="preview-badge">{badge}</span>}</h3>
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
  const [wardTrend, setWardTrend] = useState<any[]>([]);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [predictions, setPredictions] = useState<any>(null);
  const [knowledge, setKnowledge] = useState<any>(null);
  const [decisionSupport, setDecisionSupport] = useState<any>(null);
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [kpiTargets, setKpiTargets] = useState<any[]>([]);
  const [timelineDays, setTimelineDays] = useState<number>(30);
  const [escalating, setEscalating] = useState(false);
  const [activeUsers, setActiveUsers] = useState(0);
  const [digestOpen, setDigestOpen] = useState(false);
  const [digestContent, setDigestContent] = useState('');
  const [copySummaryFeedback, setCopySummaryFeedback] = useState(false);

  const [trendLabels, setTrendLabels] = useState<string[]>([]);
  const [trendComplaints, setTrendComplaints] = useState<number[]>([]);
  const [zoneAgeDist, setZoneAgeDist] = useState<any[]>([]);

  const [copilotMessages, setCopilotMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [copilotInput, setCopilotInput] = useState('');
  const [copilotLoading, setCopilotLoading] = useState(false);

  const [selectedZone, setSelectedZone] = useState<string | null>(null);

  const exportCSV = useCallback(() => {
    const rows: string[][] = [];
    const pushSection = (title: string, headers: string[], data: string[][]) => {
      rows.push([title], headers, ...data, []);
    };

    pushSection('Executive Summary — KPI', ['Metric', 'Value'], [
      ['Today Complaints', String(execSummary?.today_complaints ?? '')],
      ['Critical Incidents', String(execSummary?.critical_incidents ?? '')],
      ['Districts at Risk', String(execSummary?.districts_at_risk ?? '')],
      ['Depts Under Stress', String(execSummary?.depts_under_stress ?? '')],
      ['Avg Resolution (days)', String(execSummary?.avg_resolution_days?.toFixed(1) ?? '')],
      ['Aging >30d', String(execSummary?.aging_30d ?? '')],
    ]);

    if (wardHealth.length > 0) {
      pushSection('Ward Health', ['Ward', 'Score', 'Open Incidents', 'Critical', 'Improving', 'Trend'],
        wardHealth.map((w: any) => [w.ward ?? '', String(w.health_score ?? ''), String(w.open_incidents ?? ''), String(w.critical_incidents ?? ''), String(w.improving_flag ?? ''), String(w.trend ?? '')]));
    }

    if (deptWorkload.length > 0) {
      pushSection('Department Performance', ['Department', 'Open Incidents', 'Critical %', 'Avg Resolution (d)', 'Efficiency', 'Safety', 'Completion %'],
        deptWorkload.map((d: any) => [d.department ?? '', String(d.open_incidents ?? ''), String((d.critical_percentage ?? 0).toFixed(1)), String((d.avg_resolution_time ?? 0).toFixed(1)), String((d.efficiency ?? 0).toFixed(2)), String((d.safety ?? 0).toFixed(2)), String((d.completion_percentage ?? 0).toFixed(1))]));
    }

    if (incidents.length > 0) {
      pushSection('Incidents', ['ID', 'Priority', 'Ward', 'Department', 'Category', 'Summary', 'Status', 'Created', 'Days Open'],
        incidents.slice(0, 100).map((i: any) => [i.incident_number ?? i.id ?? '', i.priority ?? '', i.ward ?? '', i.department ?? '', i.category ?? '', (i.summary ?? '').slice(0, 80), i.status ?? '', i.created_at ?? '', String(i.days_open ?? '')]));
    }

    const recs = decisionSupport?.recommendations ?? predictions?.recommendations ?? [];
    if (recs.length > 0) {
      pushSection('AI Recommendations', ['Title', 'Priority', 'Department', 'Impact', 'Confidence'],
        recs.map((r: any) => [r.title ?? '', r.priority ?? '', r.department ?? '', String(r.expected_impact ?? ''), String(r.confidence ?? '')]));
    }

    const risks = predictions?.risks ?? [];
    if (risks.length > 0) {
      pushSection('Emerging Risks', ['Category', 'Severity', 'Reason', 'Confidence'],
        risks.map((r: any) => [r.category ?? '', r.severity ?? '', r.reason ?? '', String(r.confidence ?? '')]));
    }

    const csvContent = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `executive-report-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [execSummary, wardHealth, deptWorkload, incidents, decisionSupport, predictions]);
  const fetchAll = useCallback(async (showLoader = false) => {
    if (showLoader) setLoading(true);
    try {
      const results = await Promise.allSettled([
        api.getExecutiveSummary(),
        api.getWardHealth(),
        api.getWardTrend(),
        api.getAnomalies(),
        api.getDeptWorkload(),
        api.getIncidents(undefined, 2000),
        api.getPredictionsSummary(),
        api.getKnowledgeSummary(),
        api.getDecisionSupportSummary(),
        api.getSystemHealth().catch(() => ({})),
        api.get('/executive/kpi-targets').then(r => r.json()).catch(() => []),
        fetch(`${import.meta.env.VITE_API_BASE_URL}/dashboard/trend`).then(r => r.json()).catch(() => ({ labels: [], complaints: [], incidents: [] })),
      ]);
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
      setWardTrend(checkFeed(results[2], 'wardTrend') || []);
      setAnomalies(checkFeed(results[3], 'anomalies') || []);
      setDeptWorkload(checkFeed(results[4], 'deptWorkload') || []);
      setIncidents(checkFeed(results[5], 'incidents') || []);
      setPredictions(checkFeed(results[6], 'predictions'));
      setKnowledge(checkFeed(results[7], 'knowledge'));
      setDecisionSupport(checkFeed(results[8], 'decisionSupport'));
      setSystemHealth(checkFeed(results[9], 'systemHealth'));
      setKpiTargets(checkFeed(results[10], 'kpiTargets') || []);
      const trendRaw = checkFeed(results[11], 'trend');
      if (trendRaw && trendRaw.labels) {
        setTrendLabels(trendRaw.labels || []);
        setTrendComplaints(trendRaw.complaints || []);
      }
      const zoneDist = checkFeed(results[11], 'zoneAge');
      if (zoneDist) setZoneAgeDist(zoneDist);
      if (feedErrors.length > 0) {
        const msg = t('executive.feedErrors.someOffline') + feedErrors.join('; ');
        console.error(msg);
        if (showLoader) setError(msg);
      }
    } catch (err) {
      if (showLoader) {
        console.error('Failed to fetch executive dashboard data:', err);
        setError(t('executive.global.feedOffline'));
      }
    } finally {
      if (showLoader) setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    let mounted = true;
    const fetchWithMount = async (showLoader: boolean) => {
      if (!mounted) return;
      await fetchAll(showLoader);
    };
    fetchWithMount(true);
    const interval = setInterval(() => fetchWithMount(false), 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, [fetchAll]);

  useDashboardSocket({
    onEvent: () => { fetchAll(false); },
  });

  useEffect(() => {
    const fetchActive = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/admin/active-users`, { credentials: 'include' });
        const data = await res.json();
        setActiveUsers(data.active_users ?? 0);
      } catch {}
    };
    fetchActive();
    const interval = setInterval(fetchActive, 30000);
    return () => clearInterval(interval);
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

  const [wardPlanOpen, setWardPlanOpen] = useState(false);
  const topWardsToVisit = useMemo(() => {
    const overdueMap: Record<string, number> = {};
    (incidents || []).forEach((i: any) => {
      const w = i.ward || 'Unknown';
      if ((i.days_open ?? 0) >= 30) {
        overdueMap[w] = (overdueMap[w] || 0) + 1;
      }
    });

    const anomalyScoreMap: Record<string, number> = {};
    (anomalies || []).forEach((a: any) => {
      const w = a.ward || 'Unknown';
      anomalyScoreMap[w] = (anomalyScoreMap[w] || 0) + 1;
    });

    const wardScores: { ward: string; score: number; reason: string[] }[] = [];
    const seen = new Set<string>();

    (wardHealth || []).forEach((w: any) => {
      const name = w.ward || w.district || w.name || '';
      if (!name) return;
      const healthScore = w.healthScore ?? 100;
      const anomalyScore = anomalyScoreMap[name] || 0;
      const overdueCount = overdueMap[name] || 0;
      const combinedScore = (100 - healthScore) + (anomalyScore * 25) + (overdueCount * 15);
      const reasons: string[] = [];
      if (anomalyScore > 0) reasons.push(`High anomaly score (${anomalyScore.toFixed(1)}σ)`);
      if (overdueCount > 0) reasons.push(`${overdueCount} overdue incident${overdueCount > 1 ? 's' : ''}`);
      if (healthScore < 60) reasons.push(`Low health score (${healthScore})`);
      wardScores.push({ ward: name, score: combinedScore, reason: reasons });
      seen.add(name);
    });

    Object.keys(anomalyScoreMap).forEach(name => {
      if (!seen.has(name)) {
        wardScores.push({ ward: name, score: anomalyScoreMap[name] * 25, reason: [`High anomaly score (${anomalyScoreMap[name].toFixed(1)}σ)`] });
      }
    });

    Object.keys(overdueMap).forEach(name => {
      if (!seen.has(name) && !anomalyScoreMap[name]) {
        wardScores.push({ ward: name, score: overdueMap[name] * 15, reason: [`${overdueMap[name]} overdue incident${overdueMap[name] > 1 ? 's' : ''}`] });
      }
    });

    return wardScores.sort((a, b) => b.score - a.score).slice(0, 3);
  }, [wardHealth, anomalies, incidents]);

  const zones = useMemo(() => {
    const zoneSet = new Set<string>();
    (wardHealth || []).forEach((w: any) => {
      const zone = getCoimbatoreZone(w.ward ?? w.district ?? w.name);
      if (zone) zoneSet.add(zone);
    });
    return Array.from(zoneSet).sort();
  }, [wardHealth]);

  const filteredWardHealth = useMemo(() => {
    if (!selectedZone) return wardHealth;
    return (wardHealth || []).filter((w: any) => {
      const zone = getCoimbatoreZone(w.ward ?? w.district ?? w.name);
      return zone === selectedZone;
    });
  }, [wardHealth, selectedZone]);

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

  const generateDigest = () => {
    const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    const totalComplaints = execSummary?.today_complaints || 0;
    const resolvedCount = incidents.filter(i => i.status === 'resolved' || i.status === 'closed').length;
    const slaBreaches = '—';
    const topWard = wardHealth?.sort((a: any, b: any) => (b.healthScore || 0) - (a.healthScore || 0))[0];
    const agingCount = incidents.filter(i => (i.days_open || 0) > 30).length;
    const content = [
      `=== GIIPS Daily Digest — ${today} ===`,
      ``,
      `Today's New Complaints: ${totalComplaints}`,
      `Resolved Today: ${resolvedCount}`,
      `Critical Incidents: ${execSummary?.critical_incidents || 0}`,
      `SLA Breaches: ${slaBreaches}`,
      `Aging (>30d): ${agingCount}`,
      `Top Performing Ward: ${topWard?.ward || '—'} (Score: ${topWard?.healthScore || '—'})`,
      `Depts Under Stress: ${execSummary?.depts_under_stress || 0}`,
      ``,
      `— Generated by GIIPS Executive Dashboard`,
    ].join('\n');
    setDigestContent(content);
    setDigestOpen(true);
  };

  const [handoverOpen, setHandoverOpen] = useState(false);
  const [handoverContent, setHandoverContent] = useState('');

  const generateShiftHandover = () => {
    const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    const nextShift = new Date(Date.now() + 8 * 3600000).toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit' });
    const openCount = incidents.filter((i: any) => i.status === 'open' || i.status === 'in-progress').length;
    const criticalNow = incidents.filter((i: any) => i.priority_label?.toLowerCase() === 'critical').length;
    const aging = incidents.filter((i: any) => (i.days_open ?? 0) >= 30).length;
    const topCats = [...(deptWorkload || [])].sort((a: any, b: any) => (b.open_incidents ?? 0) - (a.open_incidents ?? 0)).slice(0, 3);
    const content = [
      `=== GIIPS Shift Handover Report ===`,
      `Date: ${today}`,
      `Next Shift Begins: ${nextShift}`,
      ``,
      `Current State:`,
      `- Open / In-Progress Incidents: ${openCount}`,
      `- Critical: ${criticalNow}`,
      `- Aging (>30d): ${aging}`,
      ``,
      `Top Departments Needing Attention:`,
      ...topCats.map((d: any) => `  ${d.department || d.name}: ${d.open_incidents ?? 0} open`),
      ``,
      `Priority Actions:`,
      ...incidents.filter((i: any) => i.priority_label?.toLowerCase() === 'critical').slice(0, 5).map((i: any) =>
        `  [${i.priority_label}] ${i.incident_number} — ${i.summary?.slice(0, 80)} (Ward ${i.ward})`
      ),
      ``,
      `— Generated by GIIPS Executive Dashboard`,
    ].join('\n');
    setHandoverContent(content);
    setHandoverOpen(true);
  };

  const copySummary = () => {
    const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    const totalComplaints = execSummary?.today_complaints ?? execSummary?.totalComplaints ?? 0;
    const totalIncidents = incidents.length;
    const resolvedCount = incidents.filter((i: any) => i.status === 'resolved' || i.status === 'closed').length;
    const resolutionRate = totalIncidents > 0 ? Math.round((resolvedCount / totalIncidents) * 100) : 0;
    const avgResDays = execSummary?.avg_resolution_days ?? execSummary?.avgResolutionTime ?? 0;
    const slaBreaches = execSummary?.sla_breaches ?? '—';
    const avgRating = execSummary?.avg_citizen_rating ?? '—';

    const topWards = [...(wardHealth || [])]
      .sort((a: any, b: any) => (b.open_incidents ?? b.openIncidents ?? 0) - (a.open_incidents ?? a.openIncidents ?? 0))
      .slice(0, 3)
      .map((w: any) => `Ward ${w.ward} (${w.open_incidents ?? w.openIncidents ?? 0})`);

    const topCats: string[] = [];
    if (deptWorkload?.length) {
      const sorted = [...deptWorkload].sort((a: any, b: any) => (b.open_incidents ?? 0) - (a.open_incidents ?? 0));
      sorted.slice(0, 3).forEach((d: any) => {
        const name = d.department || d.name || '';
        topCats.push(`${name.charAt(0).toUpperCase() + name.slice(1)} (${d.open_incidents ?? 0})`);
      });
    }

    const summary = [
      `GIIPS Executive Dashboard Summary`,
      `Date: ${today}`,
      ``,
      `Overview:`,
      `- Total Complaints: ${totalComplaints}`,
      `- Total Incidents: ${totalIncidents}`,
      `- Resolution Rate: ${resolutionRate}%`,
      `- Avg Resolution Time: ${avgResDays} days`,
      ``,
      `Top 3 Wards by Volume: ${topWards.join(', ') || '—'}`,
      `Top 3 Categories: ${topCats.join(', ') || '—'}`,
      ``,
      `SLA Breaches: ${slaBreaches}`,
      `Avg Citizen Rating: ${avgRating} / 5`,
    ].join('\n');

    navigator.clipboard.writeText(summary).then(() => {
      setCopySummaryFeedback(true);
      setTimeout(() => setCopySummaryFeedback(false), 2000);
    }).catch(() => {});
  };

  return (
    <div className="exec-dashboard">
      <Header title={t('executive.header.title')} subtitle={t('executive.header.subtitle')} />

      {error && <div className="global-banner warning"><AlertTriangle size={16} />{error}</div>}

      <div className="exec-toolbar">
        <button className="action-btn escalate-btn" onClick={autoEscalate} disabled={escalating}>
          {escalating ? <Loader2 size={14} className="spin" /> : <Zap size={14} />}
          {t('executive.runAutoEscalation')}
        </button>
        <button className="action-btn" onClick={exportCSV}>
          <Download size={14} /> {t('executive.exportCsv')}
        </button>
        <button className="action-btn" onClick={generateDigest}>
          <FileText size={14} /> {t('executive.digest.button')}
        </button>
        <button className="action-btn" onClick={copySummary}>
          <FileText size={14} /> {t('executive.copySummary.button')}
        </button>
        <button className="action-btn" onClick={generateShiftHandover}>
          <Send size={14} /> {t('executive.shiftHandover.button')}
        </button>
        <a href="/executive/department-kpis" className="action-btn" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', textDecoration: 'none' }}>
          <BarChart3 size={14} /> {t('executive.departmentKPIsLink')}
        </a>
        <a href="/executive/zone-dashboard" className="action-btn" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', textDecoration: 'none' }}>
          <MapPin size={14} /> {t('executive.zoneDashboard')}
        </a>
        {copySummaryFeedback && <span className="copy-toast">{t('executive.copySummary.copied')}</span>}
        {activeUsers > 0 && <span className="active-users-badge"><Activity size={14} /> {t('executive.activeUsers', { count: activeUsers })}</span>}
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
              <span className="kpi-label">{t('executive.agingLabel')}</span>
              <span className="kpi-value" style={agingCount > 0 ? { color: '#9333ea' } : undefined}>{agingCount}</span>
            </div>
          </div>
        </div>
      </SectionCard>

      {/* KPI Targets */}
      <SectionCard title={t('executive.kpiTargets.title')} icon={<Target size={18} />}>
        {kpiTargets.length === 0 && <p>{t('executive.kpiTargets.empty')}</p>}
        {kpiTargets.map(kt => (
          <div key={kt.id} className="kpi-target-row">
            <span className="kpi-target-name">{kt.metric_name}</span>
            <span className="kpi-target-values">
              <span>{t('executive.kpiTargets.target', { value: kt.target_value })}</span>
              {kt.current_value != null && (
                <span className={`kpi-current ${kt.current_value >= kt.target_value ? 'kpi-met' : 'kpi-not-met'}`}>
                  {t('executive.kpiTargets.current', { value: kt.current_value })}
                </span>
              )}
            </span>
          </div>
        ))}
      </SectionCard>

      {/* F7: Cost estimate */}
      {execSummary && (
        <div className="chart-card">
          <h3>{t('executive.estimatedCost')}</h3>
          <p style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f59e0b' }}>₹{execSummary.total_estimated_cost?.toLocaleString() || '0'}</p>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{t('executive.pendingRemediation')}</p>
        </div>
      )}

      {/* 2. AI Executive Brief */}
      <SectionCard title={t('executive.brief.title')} subtitle={t('executive.brief.subtitle')} icon={<Brain size={18} />} badge={t('common.preview')}>
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

      {/* Anomaly Alerts */}
      {anomalies.length > 0 && (
        <SectionCard title={t('executive.anomalies.title')} icon={<AlertTriangle size={18} />} badge={t('executive.anomalies.active', { count: anomalies.length })}>
          <div className="anomaly-list">
            {anomalies.map((a, i) => (
              <div key={i} className={`anomaly-card anomaly-${a.severity}`}>
                <span className="anomaly-severity">{a.severity}</span>
                <div>
                  <strong>{a.ward}</strong> — {a.category}
                  <p className="anomaly-detail">{a.today_count} complaints today vs avg {a.mean.toFixed(1)}</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* 3. AI Recommended Government Actions */}
      <SectionCard title={t('executive.actions.title')} subtitle={t('executive.actions.subtitle')} icon={<Target size={18} />} badge={t('common.preview')}>
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
        {zones.length > 0 && (
          <div className="zone-filter-bar">
            <span className="zone-filter-label">{t('executive.zoneFilter.label')}</span>
            {zones.map(zone => (
              <button
                key={zone}
                className={`zone-filter-btn ${selectedZone === zone ? 'active' : ''}`}
                onClick={() => setSelectedZone(selectedZone === zone ? null : zone)}
              >
                {zone}
              </button>
            ))}
            {selectedZone && (
              <button className="zone-filter-clear" onClick={() => setSelectedZone(null)}>
                {t('executive.zoneFilter.clear')}
              </button>
            )}
          </div>
        )}
        <div className="district-grid">
          <div className="district-panel">
            <h4><TrendingUp size={14} /> {t('executive.district.topPerforming')}</h4>
            {(selectedZone ? filteredWardHealth : wardHealth ? [...wardHealth].sort((a: any, b: any) => (b.healthScore || 0) - (a.healthScore || 0)).slice(0, 5) : []).map((d: any, i: number) => (
              <div key={i} className="district-row top">
                <span className="district-rank">#{i + 1}</span>
                <span className="district-name">{d.ward || d.district || d.name || `Ward ${i + 1}`}</span>
                <span className="district-score good">{(d.healthScore || d.score || 85) + '%'}</span>
                {wardTrend.length > 0 && (() => {
                  const trend = wardTrend.find((w: any) => w.ward === d.ward || w.ward === d.name);
                  if (!trend?.daily_counts) return null;
                  const counts: number[] = trend.daily_counts.map((dc: any) => dc.count);
                  const max = Math.max(...counts, 1);
                  const points = counts.map((v: number, i: number) => `${(i / (counts.length - 1)) * 58},${20 - (v / max) * 16}`).join(' ');
                  return (
                    <svg width="60" height="20" className="ward-sparkline">
                      <polyline points={points} fill="none" stroke="#3b82f6" strokeWidth="1.5" />
                    </svg>
                  );
                })()}
              </div>
            ))}
          </div>
          <div className="district-panel critical-panel">
            <h4><AlertTriangle size={14} /> {t('executive.district.mostCritical')}</h4>
            {(selectedZone ? [...filteredWardHealth].sort((a: any, b: any) => (a.healthScore || 0) - (b.healthScore || 0)).slice(0, 5) : criticalDistricts).map((d: any, i: number) => (
              <div key={i} className="district-row critical">
                <span className="district-rank">#{i + 1}</span>
                <span className="district-name">{d.ward || d.district || d.name || `Ward ${i + 1}`}</span>
                <span className="district-score bad">{(d.healthScore || d.score || 35) + '%'}</span>
                {wardTrend.length > 0 && (() => {
                  const trend = wardTrend.find((w: any) => w.ward === d.ward || w.ward === d.name);
                  if (!trend?.daily_counts) return null;
                  const counts: number[] = trend.daily_counts.map((dc: any) => dc.count);
                  const max = Math.max(...counts, 1);
                  const points = counts.map((v: number, i: number) => `${(i / (counts.length - 1)) * 58},${20 - (v / max) * 16}`).join(' ');
                  return (
                    <svg width="60" height="20" className="ward-sparkline">
                      <polyline points={points} fill="none" stroke="#3b82f6" strokeWidth="1.5" />
                    </svg>
                  );
                })()}
              </div>
            ))}
          </div>
          <div className="district-panel">
            <h4><Zap size={14} /> {t('executive.district.fastestImproving')}</h4>
            {(selectedZone ? [...filteredWardHealth].sort((a: any, b: any) => (b.healthScore || 0) - (a.healthScore || 0)).slice(0, 3) : topDistricts.slice().reverse().slice(0, 3)).map((d: any, i: number) => (
              <div key={i} className="district-row improving">
                <span className="district-rank">#{i + 1}</span>
                <span className="district-name">{d.ward || d.district || d.name || `Ward ${i + 3}`}</span>
                <span className="district-score good">+{(d.trend || d.improvement || 12)}%</span>
              </div>
            ))}
          </div>
          <div className="district-panel warning-panel">
            <h4><Flame size={14} /> {t('executive.district.highestGrowth')}</h4>
            {(selectedZone ? [...filteredWardHealth].sort((a: any, b: any) => (a.healthScore || 0) - (b.healthScore || 0)).slice(0, 3) : criticalDistricts.slice(0, 3)).map((d: any, i: number) => (
              <div key={i} className="district-row growth">
                <span className="district-rank">#{i + 1}</span>
                <span className="district-name">{d.ward || d.district || d.name || `Ward ${i + 5}`}</span>
                <span className="district-score bad">+{(d.growth || d.complaintGrowth || 28)}%</span>
              </div>
            ))}
          </div>
        </div>
      </SectionCard>

      {/* Ward Visit Planner */}
      <SectionCard
        title={t('executive.wardPlanner.title')}
        subtitle={t('executive.wardPlanner.subtitle')}
        icon={<MapPin size={18} />}
      >
        <div className="ward-plan-header" style={{ marginBottom: 12 }}>
          <button
            className="ward-plan-toggle"
            onClick={() => setWardPlanOpen(!wardPlanOpen)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 16px', background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: 8, color: '#3b82f6', fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}
          >
            <MapPin size={16} />
            {wardPlanOpen ? t('executive.wardPlanner.hideRecommendations') : topWardsToVisit.length === 1 ? t('executive.wardPlanner.showRecommendations', { count: 1 }) : t('executive.wardPlanner.showRecommendationsPlural', { count: topWardsToVisit.length })}
            <ChevronDown size={14} style={{ transform: wardPlanOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
          </button>
        </div>
        {wardPlanOpen && (
          <div className="ward-plan-list" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {topWardsToVisit.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: 13, padding: 16, textAlign: 'center' }}>{t('executive.wardPlanner.empty')}</p>
            ) : (
              topWardsToVisit.map((w, i) => (
                <div key={w.ward} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: 14, background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 8, borderLeft: `3px solid ${i === 0 ? '#dc2626' : i === 1 ? '#f59e0b' : '#3b82f6'}` }}>
                  <div style={{ width: 28, height: 28, borderRadius: '50%', background: i === 0 ? '#dc2626' : i === 1 ? '#f59e0b' : '#3b82f6', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, flexShrink: 0 }}>#{i + 1}</div>
                  <div style={{ flex: 1 }}>
                    <strong style={{ fontSize: 14, color: 'var(--text-primary)' }}>{w.ward}</strong>
                    <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{w.reason.join(', ') || t('executive.wardPlanner.needsInspection')}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
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

      {/* Zone Age Distribution */}
      {zoneAgeDist.length > 0 && (
        <SectionCard title={t('executive.zoneAge.title')} icon={<BarChart3 size={18} />}>
          <Plot data={[{
            x: zoneAgeDist.map((z: any) => z.zone),
            y: zoneAgeDist.map((z: any) => z['0-7d']), name: t('executive.zoneAge.bucket0to7'), type: 'bar'
          }, {
            x: zoneAgeDist.map((z: any) => z.zone),
            y: zoneAgeDist.map((z: any) => z['7-30d']), name: t('executive.zoneAge.bucket7to30'), type: 'bar'
          }, {
            x: zoneAgeDist.map((z: any) => z.zone),
            y: zoneAgeDist.map((z: any) => z['30-90d']), name: t('executive.zoneAge.bucket30to90'), type: 'bar'
          }, {
            x: zoneAgeDist.map((z: any) => z.zone),
            y: zoneAgeDist.map((z: any) => z['90d+']), name: t('executive.zoneAge.bucket90plus'), type: 'bar'
          }]} layout={{barmode: 'stack', title: '', width: null, height: 300, autosize: true, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: {color: 'var(--text-primary)'}, legend: {orientation: 'h', y: -0.2}}} config={{displayModeBar: false, responsive: true}} />
        </SectionCard>
      )}

      {/* 8. AI Copilot */}
      <SectionCard title={t('executive.copilot.title')} subtitle={t('executive.copilot.subtitle')} icon={<Bot size={18} />} badge={t('common.preview')}>
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
      <SectionCard title={t('executive.resources.title')} subtitle={t('executive.resources.subtitle')} icon={<Users size={18} />} badge={t('common.preview')}>
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

      {digestOpen && (
          <div className="digest-modal" onClick={() => setDigestOpen(false)}>
            <div className="digest-modal-content" onClick={e => e.stopPropagation()}>
              <h3>{t('executive.digest.title')}</h3>
              <pre>{digestContent}</pre>
              <div className="digest-actions">
                <button className="copy-btn" onClick={() => { navigator.clipboard.writeText(digestContent); }}>{t('executive.digest.copy')}</button>
                <button className="close-btn" onClick={() => setDigestOpen(false)}>{t('executive.digest.close')}</button>
              </div>
            </div>
          </div>
        )}

      {handoverOpen && (
        <div className="digest-modal" onClick={() => setHandoverOpen(false)}>
          <div className="digest-modal-content" onClick={e => e.stopPropagation()}>
            <h3>{t('executive.shiftHandover.title')}</h3>
            <pre>{handoverContent}</pre>
            <div className="digest-actions">
              <button className="copy-btn" onClick={() => { navigator.clipboard.writeText(handoverContent); }}>{t('executive.shiftHandover.copy')}</button>
              <button className="close-btn" onClick={() => setHandoverOpen(false)}>{t('executive.shiftHandover.close')}</button>
            </div>
          </div>
        </div>
      )}

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
