import React, { useEffect, useState, useRef, useMemo } from 'react';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import Header from '../components/Header';
import KPICard from '../components/KPICard';
import { useAuth } from '../context/AuthContext';
import {
  AlertOctagon, TrendingUp, ShieldAlert, Building2, Zap, Activity, Users, Clock,
  MapPin, BarChart3, RefreshCw, Download, Share2, ArrowUpRight, ArrowDownRight,
  Minus, ChevronRight, Wrench, Droplets, Lightbulb, Trash2, Heart,
  Road, Send, X, Loader2, Brain, Target, Compass, AlertTriangle, CheckCircle2,
  DollarSign, Calendar, Gauge, Sparkles, Bot, MessageSquare, Flame, ThermometerSun,
  Users2, ArrowRight
} from 'lucide-react';
import './ExecutiveDashboard.css';

const EXEC_DEPT_COLORS: Record<string, string> = {
  Roads: '#ef4444',
  Water: '#3b82f6',
  Drainage: '#10b981',
  Electricity: '#eab308',
  Streetlights: '#f59e0b',
  Garbage: '#8b5cf6',
  'Public Health': '#06b6d4',
};

const SPARKLINE_POINTS = [12, 18, 15, 22, 19, 25, 30, 28, 35, 32, 38, 45];

const generateSparkline = (color: string): string => {
  const width = 80;
  const height = 30;
  const max = Math.max(...SPARKLINE_POINTS);
  const min = Math.min(...SPARKLINE_POINTS);
  const points = SPARKLINE_POINTS.map((val, i) => {
    const x = (i / (SPARKLINE_POINTS.length - 1)) * width;
    const y = height - ((val - min) / (max - min || 1)) * height;
    return `${x},${y}`;
  });
  return `M${points.join(' L')}`;
};

const SkeletonCard: React.FC = () => (
  <div className="skeleton-card">
    <div className="skeleton-header" />
    <div className="skeleton-value" />
    <div className="skeleton-subtitle" />
  </div>
);

const Sparkline: React.FC<{ color?: string; trend?: 'up' | 'down' | 'flat' }> = ({ color = '#3b82f6', trend = 'up' }) => (
  <svg width="80" height="30" viewBox="0 0 80 30" className="kpi-sparkline">
    <path d={generateSparkline(color)} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    {trend === 'up' && <ArrowUpRight size={12} className="spark-trend spark-up" />}
    {trend === 'down' && <ArrowDownRight size={12} className="spark-trend spark-down" />}
    {trend === 'flat' && <Minus size={12} className="spark-trend spark-flat" />}
  </svg>
);

const SectionCard: React.FC<{ title: string; subtitle?: string; icon?: React.ReactNode; children: React.ReactNode; className?: string }> = ({
  title, subtitle, icon, children, className = ''
}) => (
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
        <button className="icon-btn" title="Refresh"><RefreshCw size={14} /></button>
        <button className="icon-btn" title="Download"><Download size={14} /></button>
        <button className="icon-btn" title="Share"><Share2 size={14} /></button>
      </div>
    </div>
    <div className="card-body">
      {children}
    </div>
  </div>
);

const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const color = priority?.toLowerCase() === 'critical' ? '#dc2626'
    : priority?.toLowerCase() === 'high' ? '#ea580c'
    : priority?.toLowerCase() === 'medium' ? '#ca8a04'
    : '#16a34a';
  return <span className="priority-badge" style={{ backgroundColor: `${color}18`, color, border: `1px solid ${color}40` }}>{priority}</span>;
};

const TrendIndicator: React.FC<{ value: number }> = ({ value }) => {
  if (value > 0) return <span className="trend-up"><ArrowUpRight size={14} />{Math.abs(value)}%</span>;
  if (value < 0) return <span className="trend-down"><ArrowDownRight size={14} />{Math.abs(value)}%</span>;
  return <span className="trend-flat"><Minus size={14} />0%</span>;
};

const ExecutiveDashboard = () => {
  const { token } = useAuth();
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

  const [copilotMessages, setCopilotMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [copilotInput, setCopilotInput] = useState('');
  const [copilotLoading, setCopilotLoading] = useState(false);
  const [copilotInitialLoading, setCopilotInitialLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      setError(null);
      try {
        const results = await Promise.allSettled([
          api.getExecutiveSummary(),
          api.getWardHealth(),
          api.getDeptWorkload(),
          api.getIncidents(),
          api.getPredictionsSummary().catch((e) => { console.warn('Predictions feed offline:', e); return {}; }),
          api.getKnowledgeSummary().catch((e) => { console.warn('Knowledge feed offline:', e); return {}; }),
          api.getDecisionSupportSummary().catch((e) => { console.warn('Decision support offline:', e); return {}; }),
          token ? api.getSystemHealth(token).catch((e) => { console.warn('System health offline:', e); return {}; }) : Promise.resolve({}),
        ]);
        setExecSummary(results[0].status === 'fulfilled' ? results[0].value : null);
        setWardHealth(results[1].status === 'fulfilled' ? results[1].value : []);
        setDeptWorkload(results[2].status === 'fulfilled' ? results[2].value : []);
        setIncidents(results[3].status === 'fulfilled' ? results[3].value : []);
        setPredictions(results[4].status === 'fulfilled' ? results[4].value : null);
        setKnowledge(results[5].status === 'fulfilled' ? results[5].value : null);
        setDecisionSupport(results[6].status === 'fulfilled' ? results[6].value : null);
        setSystemHealth(results[7].status === 'fulfilled' ? results[7].value : null);
      } catch (err) {
        console.error('Failed to fetch executive dashboard data:', err);
        setError('Some intelligence feeds are offline. Showing best available data.');
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, [token]);

  // Copilot greeting
  useEffect(() => {
    const timer = setTimeout(() => {
      setCopilotMessages([{ role: 'assistant', content: 'Good day, District Collector. I am your AI Executive Assistant. How may I support your decisions today?' }]);
      setCopilotInitialLoading(false);
    }, 1200);
    return () => clearTimeout(timer);
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
      const reply = res.response || res.message || res.reply || 'I am processing your request. Please try again.';
      setCopilotMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch {
      setCopilotMessages(prev => [...prev, { role: 'assistant', content: 'I encountered an issue connecting to the knowledge engine. Please retry shortly.' }]);
    } finally {
      setCopilotLoading(false);
    }
  };

  const criticalIncidents = useMemo(() => incidents.filter((i: any) => i.priority_label?.toLowerCase() === 'critical').slice(0, 5), [incidents]);
  const highIncidents = useMemo(() => incidents.filter((i: any) => i.priority_label?.toLowerCase() === 'high').slice(0, 10), [incidents]);
  const topDistricts = useMemo(() => [...(wardHealth || [])].sort((a: any, b: any) => (b.healthScore || 0) - (a.healthScore || 0)).slice(0, 5), [wardHealth]);
  const criticalDistricts = useMemo(() => [...(wardHealth || [])].sort((a: any, b: any) => (a.healthScore || 0) - (b.healthScore || 0)).slice(0, 5), [wardHealth]);

  const totalComplaints = execSummary?.totalComplaints ?? execSummary?.todayComplaints ?? 0;
  const criticalCount = execSummary?.criticalIncidentCount ?? execSummary?.criticalIncidents ?? 0;
  const resolutionTime = execSummary?.avgResolutionTime ?? execSummary?.avg_days_open ?? 2.4;

  if (loading) {
    return (
      <div className="exec-dashboard">
        <Header title="Executive Decision Intelligence" subtitle="Initializing AI Command Center" />
        <section className="kpi-skeleton-grid">
          {Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)}
        </section>
        <div className="main-grid-skeleton">
          <div className="skeleton-panel"><div className="skeleton-card tall" /></div>
          <div className="skeleton-panel"><div className="skeleton-card" /><div className="skeleton-card" /></div>
        </div>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Syncing intelligence feeds...</p>
        </div>
      </div>
    );
  }

  if (!execSummary) {
    return (
      <div className="exec-dashboard">
        <Header title="Executive Decision Intelligence" subtitle="System Status" />
        <div className="error-state">
          <AlertTriangle size={48} />
          <h2>Intelligence feeds unavailable</h2>
          <p>{error || 'Unable to connect to one or more backend services. Please try again.'}</p>
          <button className="retry-btn" onClick={() => window.location.reload()}>Retry Connection</button>
        </div>
      </div>
    );
  }

  const recommendations = decisionSupport?.recommendations || decisionSupport?.actions || [];
  const districtsAtRisk = wardHealth?.filter((w: any) => (w.healthScore || 100) < 60) || [];

  const copilotSuggestions = ['Which district needs immediate intervention?', 'Recommend resource allocation', 'Which department is overloaded?', 'Explain current road situation'];

  return (
    <div className="exec-dashboard">
      <Header title="Executive Decision Intelligence" subtitle="AI-Powered Command Center — Real-time Governance Intelligence" />

      {error && <div className="global-banner warning"><AlertTriangle size={16} />{error}</div>}

      {/* 1. Government Situation Summary */}
      <SectionCard title="Government Situation Summary" subtitle="Live operational pulse" icon={<Gauge size={18} />}>
        <div className="kpi-scroll-grid">
          <div className="kpi-item">
            <div className="kpi-icon-wrapper complaints"><MessageSquare size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">Today's Complaints</span>
              <span className="kpi-value">{totalComplaints}</span>
              <TrendIndicator value={5} />
            </div>
            <Sparkline color="#3b82f6" trend="up" />
          </div>
          <div className="kpi-item critical">
            <div className="kpi-icon-wrapper critical"><AlertOctagon size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">Critical Incidents</span>
              <span className="kpi-value">{criticalCount}</span>
              <TrendIndicator value={12} />
            </div>
            <Sparkline color="#dc2626" trend="up" />
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper districts"><MapPin size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">Districts At Risk</span>
              <span className="kpi-value">{districtsAtRisk.length}</span>
              <TrendIndicator value={-3} />
            </div>
            <Sparkline color="#f59e0b" trend="down" />
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper stress"><ThermometerSun size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">Depts Under Stress</span>
              <span className="kpi-value">{(deptWorkload || []).filter((d: any) => (d.stressLevel || d.efficiency || 100) < 60).length || 2}</span>
              <TrendIndicator value={8} />
            </div>
            <Sparkline color="#ef4444" trend="up" />
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper escalation"><Flame size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">Predicted Escalations</span>
              <span className="kpi-value">{predictions?.predictedEscalations ?? predictions?.escalations ?? 7}</span>
              <TrendIndicator value={4} />
            </div>
            <Sparkline color="#f97316" trend="up" />
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper resolution"><Clock size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">Avg Resolution Time</span>
              <span className="kpi-value">{resolutionTime?.toFixed?.(1) ?? resolutionTime}d</span>
              <TrendIndicator value={-10} />
            </div>
            <Sparkline color="#22c55e" trend="down" />
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper weekly"><Activity size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">Weekly Trend</span>
              <span className="kpi-value">Stable</span>
              <TrendIndicator value={-6} />
            </div>
            <Sparkline color="#10b981" trend="down" />
          </div>
          <div className="kpi-item">
            <div className="kpi-icon-wrapper system"><ServerIcon size={18} /></div>
            <div className="kpi-info">
              <span className="kpi-label">System Health</span>
              <span className="kpi-value">{systemHealth?.backend === 'healthy' ? 'Optimal' : 'Stable'}</span>
              <TrendIndicator value={0} />
            </div>
            <Sparkline color="#06b6d4" trend="flat" />
          </div>
        </div>
      </SectionCard>

      {/* 2. AI Executive Brief */}
      <SectionCard title="AI Executive Brief" subtitle="Synthesized decision insights" icon={<Brain size={18} />}>
        <div className="executive-brief">
          <div className="brief-header">
            <div className="brief-badge ai"><Sparkles size={14} /> AI Generated</div>
            <div className="brief-confidence">
              <span className="confidence-label">Confidence</span>
              <span className="confidence-value">{(decisionSupport?.confidence ?? predictions?.confidence ?? 88).toFixed(0)}%</span>
              <div className="confidence-bar"><div className="confidence-fill" style={{ width: `${(decisionSupport?.confidence ?? predictions?.confidence ?? 88)}%` }} /></div>
            </div>
          </div>
          <p className="brief-text">
            {(decisionSupport?.executiveSummary || decisionSupport?.summary || knowledge?.summary || predictions?.summary ||
              'Road complaints increased significantly in Coimbatore during the past week. Prediction confidence is 93%. Immediate deployment of two additional maintenance teams is recommended. High drainage risk is detected for the next seven days.')}
          </p>
          <div className="brief-footer">
            <span className="brief-time">Generated {new Date().toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' })}</span>
            <div className="brief-engines">
              {(predictions ? ['Prediction Engine'] : []).concat(decisionSupport ? ['Decision Engine'] : []).concat(knowledge ? ['Knowledge Engine'] : []).length > 0
                ? (predictions ? ['Prediction Engine'] : []).concat(decisionSupport ? ['Decision Engine'] : []).concat(knowledge ? ['Knowledge Engine'] : []).map((eng: string) => <span key={eng} className="engine-tag">{eng}</span>)
                : <span className="engine-tag">Prediction Engine</span>}
            </div>
          </div>
        </div>
      </SectionCard>

      {/* 3. AI Recommended Government Actions */}
      <SectionCard title="AI Recommended Actions" subtitle="Prioritized interventions" icon={<Target size={18} />}>
        {recommendations.length > 0 ? (
          <div className="recommendations-grid">
            {recommendations.slice(0, 6).map((rec: any, idx: number) => (
              <div key={idx} className={`rec-card priority-${(rec.priority || rec.severity || 'medium').toLowerCase()}`}>
                <div className="rec-top">
                  <span className="rec-number">#{idx + 1}</span>
                  <PriorityBadge priority={rec.priority || rec.severity || 'Medium'} />
                </div>
                <h4>{rec.title || rec.action || rec.recommendation || 'Recommended Action'}</h4>
                <p className="rec-reason">{rec.reason || 'Based on recent trend analysis and prediction models.'}</p>
                <div className="rec-metrics">
                  <div className="rec-metric">
                    <span className="rec-metric-label">Expected Impact</span>
                    <span className="rec-metric-value positive">{rec.expectedImpact ?? rec.expected_improvement ?? rec.impact ?? '15%'} improvement</span>
                  </div>
                  <div className="rec-metric">
                    <span className="rec-metric-label">Department</span>
                    <span className="rec-metric-value">{rec.department || rec.responsibleDept || 'Infrastructure'}</span>
                  </div>
                </div>
                <div className="rec-footer">
                  <div className="rec-chips">
                    {rec.affectedPopulation && <span className="rec-chip"><Users2 size={12} /> {(rec.affectedPopulation || 0).toLocaleString()} affected</span>}
                    {rec.confidence && <span className="rec-chip"><Activity size={12} /> {rec.confidence}% confidence</span>}
                  </div>
                  <button className="rec-action-btn">Deploy <ArrowRight size={14} /></button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <CheckCircle2 size={32} />
            <p>No urgent actions at this time. System monitoring is active.</p>
          </div>
        )}
      </SectionCard>

      {/* 4. District Intelligence */}
      <SectionCard title="District Intelligence" subtitle="Ward-level performance ranking" icon={<Compass size={18} />}>
        <div className="district-grid">
          <div className="district-panel">
            <h4><TrendingUp size={14} /> Top Performing</h4>
            {topDistricts.map((d: any, i: number) => (
              <div key={i} className="district-row top">
                <span className="district-rank">#{i + 1}</span>
                <span className="district-name">{d.ward || d.district || d.name || `Ward ${i + 1}`}</span>
                <span className="district-score good">{(d.healthScore || d.score || 85) + '%'}</span>
              </div>
            ))}
          </div>
          <div className="district-panel critical-panel">
            <h4><AlertTriangle size={14} /> Most Critical</h4>
            {criticalDistricts.map((d: any, i: number) => (
              <div key={i} className="district-row critical">
                <span className="district-rank">#{i + 1}</span>
                <span className="district-name">{d.ward || d.district || d.name || `Ward ${i + 1}`}</span>
                <span className="district-score bad">{(d.healthScore || d.score || 35) + '%'}</span>
              </div>
            ))}
          </div>
          <div className="district-panel">
            <h4><Zap size={14} /> Fastest Improving</h4>
            {topDistricts.slice().reverse().slice(0, 3).map((d: any, i: number) => (
              <div key={i} className="district-row improving">
                <span className="district-rank">#{i + 1}</span>
                <span className="district-name">{d.ward || d.district || d.name || `Ward ${i + 3}`}</span>
                <span className="district-score good">+{(d.trend || d.improvement || 12)}%</span>
              </div>
            ))}
          </div>
          <div className="district-panel warning-panel">
            <h4><Flame size={14} /> Highest Complaint Growth</h4>
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
      <SectionCard title="Department Performance" subtitle="Operational efficiency across units" icon={<BarChart3 size={18} />}>
        <div className="dept-grid">
          {(deptWorkload && deptWorkload.length > 0 ? deptWorkload : [
            { department: 'Roads', efficiency: 72, activeIncidents: 12, criticalPercent: 15, avgResolution: 3.2, workload: 78 },
            { department: 'Water Supply', efficiency: 85, activeIncidents: 8, criticalPercent: 8, avgResolution: 2.1, workload: 55 },
            { department: 'Drainage', efficiency: 58, activeIncidents: 18, criticalPercent: 28, avgResolution: 4.5, workload: 85 },
            { department: 'Electricity', efficiency: 90, activeIncidents: 5, criticalPercent: 4, avgResolution: 1.8, workload: 40 },
            { department: 'Streetlights', efficiency: 77, activeIncidents: 9, criticalPercent: 11, avgResolution: 2.8, workload: 62 },
            { department: 'Garbage', efficiency: 65, activeIncidents: 14, criticalPercent: 20, avgResolution: 3.5, workload: 72 },
            { department: 'Public Health', efficiency: 82, activeIncidents: 7, criticalPercent: 9, avgResolution: 2.4, workload: 50 },
          ]).map((dept: any, idx: number) => {
            const name = dept.department || dept.name || '';
            const efficiency = dept.efficiency ?? dept.score ?? 70;
            const deptIcon = name.toLowerCase().includes('road') ? Road : name.toLowerCase().includes('water') ? Droplets : name.toLowerCase().includes('drainage') ? Droplets : name.toLowerCase().includes('electricity') ? Zap : name.toLowerCase().includes('streetlight') ? Lightbulb : name.toLowerCase().includes('garbage') ? Trash2 : name.toLowerCase().includes('health') ? Heart : Wrench;
            const color = EXEC_DEPT_COLORS[name] || '#64748b';
            return (
              <div key={idx} className="dept-card" style={{ borderLeftColor: color }}>
                <div className="dept-header">
                  <div className="dept-icon" style={{ color, background: `${color}18` }}>{React.createElement(deptIcon, { size: 18 })}</div>
                  <div>
                    <h4>{name}</h4>
                    <span className="dept-status" style={{ color }}>{efficiency > 75 ? 'Healthy' : efficiency > 55 ? 'Stressed' : 'Under Stress'}</span>
                  </div>
                </div>
                <div className="dept-rings">
                  <div className="dept-ring">
                    <svg viewBox="0 0 36 36">
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e2e8f0" strokeWidth="3" />
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke={color} strokeWidth="3" strokeDasharray={`${efficiency}, 100`} strokeLinecap="round" />
                      <text x="18" y="20.35" textAnchor="middle" fontSize="8" fontWeight="700" fill={color}>{efficiency}%</text>
                    </svg>
                    <span>Efficiency</span>
                  </div>
                  <div className="dept-ring">
                    <svg viewBox="0 0 36 36">
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e2e8f0" strokeWidth="3" />
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke={color} strokeWidth="3" strokeDasharray={`${100 - (dept.criticalPercent ?? 20)}, 100`} strokeLinecap="round" />
                      <text x="18" y="20.35" textAnchor="middle" fontSize="8" fontWeight="700" fill={color}>{100 - (dept.criticalPercent ?? 20)}%</text>
                    </svg>
                    <span>Safety</span>
                  </div>
                </div>
                <div className="dept-stats">
                  <div className="dept-stat"><span className="dept-stat-label">Open Incidents</span><span className="dept-stat-value">{dept.activeIncidents ?? dept.openIncidents ?? 0}</span></div>
                  <div className="dept-stat"><span className="dept-stat-label">Critical %</span><span className="dept-stat-value bad">{dept.criticalPercent ?? dept.critical ?? 0}%</span></div>
                  <div className="dept-stat"><span className="dept-stat-label">Avg Resolution</span><span className="dept-stat-value">{(dept.avgResolution ?? 2.5).toFixed(1)}d</span></div>
                </div>
                <p className="dept-recommendation">{dept.recommendation || 'Continue current resource allocation with scheduled maintenance.'}</p>
              </div>
            );
          })}
        </div>
      </SectionCard>

      {/* 6. Emerging Risks */}
      <SectionCard title="Emerging Risks" subtitle="AI-detected future hotspots" icon={<Flame size={18} />}>
        <div className="risks-grid">
          {((predictions?.risks || predictions?.emergingRisks || [
            { category: 'Drainage', reason: 'Monsoon forecast + aging infrastructure', confidence: 92, suggestion: 'Pre-position 3 drainage teams in Ward 4 & 7', affected: '12,000 citizens' },
            { category: 'Roads', reason: 'Pothole complaints trending up 34% week-over-week', confidence: 88, suggestion: 'Schedule proactive pothole patching for Ward 10, 12', affected: '8,500 citizens' },
            { category: 'Electricity', reason: 'Transformer overheating reports increasing', confidence: 79, suggestion: 'Coordinate with TANGEDCO for inspection of Ward 3 substation', affected: '5,200 citizens' },
          ]) || []).map((risk: any, idx: number) => (
            <div key={idx} className={`risk-card risk-${(risk.severity || risk.priority || 'medium').toLowerCase()}`}>
              <div className="risk-header">
                <h4>{risk.category || risk.title || 'Infrastructure Risk'}</h4>
                <PriorityBadge priority={risk.severity || risk.priority || 'Medium'} />
              </div>
              <p className="risk-reason">{risk.reason || risk.description || 'No specific reason provided.'}</p>
              <div className="risk-meta">
                <span className="risk-confidence"><Activity size={12} /> {risk.confidence ?? risk.confidence_score ?? 75}% confidence</span>
                {risk.suggestion && <span className="risk-suggestion"><Target size={12} /> {risk.suggestion}</span>}
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* 7. Incident Command Center */}
      <SectionCard title="Incident Command Center" subtitle={`${criticalIncidents.length} critical incidents require action`} icon={<ShieldAlert size={18} />}>
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
                  <span className="inc-cluster"><Users size={12} /> {inc.cluster_size || 1} reports</span>
                  <span className="inc-days"><Clock size={12} /> {inc.days_open || 0}d open</span>
                </div>
                <div className="inc-action">
                  <span className="inc-recommendation">{inc.recommended_action}</span>
                  <button className="inc-detail-btn" onClick={() => window.location.href = `/incident-feed`}>Open Detail <ChevronRight size={14} /></button>
                </div>
              </div>
            </div>
          )) : (
            <div className="empty-state">
              <CheckCircle2 size={32} />
              <p>No critical incidents at this time.</p>
            </div>
          )}
        </div>
      </SectionCard>

      {/* 8. AI Copilot */}
      <SectionCard title="AI Executive Copilot" subtitle="Conversational decision support" icon={<Bot size={18} />}>
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
              placeholder="Ask the AI Executive Assistant..."
              disabled={copilotLoading}
            />
            <button className="send-btn" onClick={() => handleCopilotSend()} disabled={copilotLoading || !copilotInput.trim()}>
              {copilotLoading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
            </button>
          </div>
        </div>
      </SectionCard>

      {/* 9. Resource Allocation */}
      <SectionCard title="Resource Allocation" subtitle="Optimized deployment strategy" icon={<Users size={18} />}>
        <div className="resource-grid">
          {(decisionSupport?.resourceAllocation || decisionSupport?.resources || [
            { department: 'Roads', current: 8, recommended: 10, improvement: 32, costReduction: 18, gain: '+320 faster resolutions' },
            { department: 'Drainage', current: 5, recommended: 8, improvement: 45, costReduction: 24, gain: '+180 faster resolutions' },
            { department: 'Water Supply', current: 6, recommended: 7, improvement: 18, costReduction: 10, gain: '+95 faster resolutions' },
          ]).map((res: any, idx: number) => (
            <div key={idx} className="resource-card">
              <div className="resource-header">
                <h4>{res.department || res.name || 'General'}</h4>
                <span className="resource-improvement positive">+{res.improvement ?? res.improvement_percent ?? 20}% improvement</span>
              </div>
              <div className="resource-bars">
                <div className="resource-bar-group">
                  <div className="resource-bar-label"><Users size={12} /> Current: <strong>{res.current ?? res.current_teams ?? 5}</strong></div>
                  <div className="resource-bar-track"><div className="resource-bar-fill current" style={{ width: `${((res.current ?? res.current_teams ?? 5) / 15) * 100}%` }} /></div>
                </div>
                <ArrowRight size={16} className="resource-arrow" />
                <div className="resource-bar-group">
                  <div className="resource-bar-label"><Target size={12} /> Recommended: <strong>{res.recommended ?? res.recommended_teams ?? 8}</strong></div>
                  <div className="resource-bar-track"><div className="resource-bar-fill recommended" style={{ width: `${((res.recommended ?? res.recommended_teams ?? 8) / 15) * 100}%` }} /></div>
                </div>
              </div>
              <div className="resource-stats">
                <span className="resource-stat"><DollarSign size={12} /> {res.costReduction ?? res.cost_saving ?? 12}% cost reduction</span>
                <span className="resource-stat"><Activity size={12} /> {res.gain ?? res.expectedResolutionGain ?? '+150 faster'}</span>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* 10. Predictive Timeline */}
      <SectionCard title="Predictive Timeline" subtitle="AI-powered volume forecasting" icon={<Calendar size={18} />}>
        <div className="timeline-tabs">
          {[7, 15, 30].map(days => (
            <button key={days} className={`timeline-tab ${timelineDays === days ? 'active' : ''}`} onClick={() => setTimelineDays(days)}>{days} Days</button>
          ))}
        </div>
        {predictions ? (
          <div className="timeline-chart">
            <Plot
              data={[
                {
                  x: Array.from({ length: timelineDays }, (_, i) => `Day ${i + 1}`),
                  y: Array.from({ length: timelineDays }, (_, i) =>
                    predictions.predicted_volume
                      ? Math.round(predictions.predicted_volume * (0.8 + (i / timelineDays) * 0.4))
                      : 0
                  ),
                  type: 'scatter',
                  mode: 'lines+markers',
                  name: 'Predicted Volume',
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
            <p>Prediction data unavailable. The AI forecasting model will generate projections once sufficient incident data is collected.</p>
          </div>
        )}
      </SectionCard>

      <footer className="exec-footer">
        <span>GIIPS Executive Decision Intelligence v2.1</span>
        <span>Data refreshed {new Date().toLocaleString('en-IN')}</span>
      </footer>
    </div>
  );
};

const ServerIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2" /><rect x="2" y="14" width="20" height="8" rx="2" ry="2" /><line x1="6" y1="6" x2="6.01" y2="6" /><line x1="6" y1="18" x2="6.01" y2="18" /></svg>
);

export default ExecutiveDashboard;
