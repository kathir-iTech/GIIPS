import { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../services/api';
import type { Incident, Complaint, PriorityHistory } from '../types';
import Header from '../components/Header';
import {
  Brain, ShieldAlert, MapPin, Clock, GitBranch, Lightbulb, Users, Wrench,
  ChevronRight, ChevronLeft, Search, Filter, SortAsc, ArrowUpRight, AlertTriangle,
  Loader2, Target, Flame, Calendar, BookOpen, Zap, CheckCircle2, X, Building2
} from 'lucide-react';
import './Clusters.css';

type SortField = 'priority_score' | 'cluster_size' | 'days_open' | 'incident_number' | 'ward';
type PriorityLevel = 'Critical' | 'High' | 'Medium' | 'Low';

interface PriorityRule {
  id: string;
  name: string;
  weight: number;
  description: string;
}

interface KnowledgeInsight {
  title: string;
  category: string;
  statement: string;
  related_incidents: number;
}

interface DecisionRecommendation {
  title: string;
  priority: string;
  department: string;
  reason: string;
  expected_impact: string;
  confidence: number;
}

interface PredictionData {
  summary: string;
  predictedEscalations: number;
  risks: Array<{
    category: string;
    reason: string;
    confidence: number;
    suggestion: string;
    affected: string;
  }>;
}

interface KnowledgeData {
  summary: string;
  insights: KnowledgeInsight[];
}

interface DecisionData {
  summary: string;
  confidence: number;
  recommendations: DecisionRecommendation[];
  resourceAllocation: Array<{
    department: string;
    current: number;
    recommended: number;
    improvement: number;
    costReduction: number;
    gain: string;
  }>;
}

const ITEMS_PER_PAGE = 8;

const getPriorityColor = (label?: string) => {
  const l = (label || '').toLowerCase();
  if (l === 'critical') return '#dc2626';
  if (l === 'high') return '#ea580c';
  if (l === 'medium') return '#ca8a04';
  return '#16a34a';
};

const getPriorityBg = (label?: string) => {
  const l = (label || '').toLowerCase();
  if (l === 'critical') return 'rgba(220,38,38,0.08)';
  if (l === 'high') return 'rgba(234,88,12,0.08)';
  if (l === 'medium') return 'rgba(202,138,4,0.08)';
  return 'rgba(22,163,74,0.08)';
};

const SectionCard: React.FC<{
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  accent?: string;
  children: React.ReactNode;
  className?: string;
}> = ({ title, subtitle, icon, accent, children, className = '' }) => (
  <div className={`section-card glass-card ${className}`} style={accent ? { borderLeft: `3px solid ${accent}` } : undefined}>
    <div className="card-header">
      <div className="card-title-group">
        {icon && <span className="card-icon">{icon}</span>}
        <div>
          <h3>{title}</h3>
          {subtitle && <span className="card-subtitle">{subtitle}</span>}
        </div>
      </div>
    </div>
    <div className="card-body">
      {children}
    </div>
  </div>
);

const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const color = getPriorityColor(priority);
  return (
    <span className="priority-badge" style={{ backgroundColor: `${color}18`, color, border: `1px solid ${color}40` }}>
      {priority}
    </span>
  );
};

const INITIAL_SUMMARY = 'Investigate incident based on linked complaints and AI analysis.';
const DEFAULT_RECOMMENDATION = 'Issue requires immediate attention and resource deployment.';

const Clusters = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [priorityRules, setPriorityRules] = useState<any[]>([]);
  const [predictions, setPredictions] = useState<PredictionData | null>(null);
  const [knowledge, setKnowledge] = useState<KnowledgeData | null>(null);
  const [decisionSupport, setDecisionSupport] = useState<DecisionData | null>(null);

  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [intelLoading, setIntelLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [workspaceOpen, setWorkspaceOpen] = useState(false);

  const [search, setSearch] = useState('');
  const [filterPriority, setFilterPriority] = useState<PriorityLevel | 'all'>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterWard, setFilterWard] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('priority_score');
  const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    const fetchPageData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [incs, rules, preds, know, dec] = await Promise.allSettled([
          api.getIncidents(),
          api.getPriorityRules().catch(() => []),
          api.getPredictionsSummary().catch(() => null),
          api.getKnowledgeSummary().catch(() => null),
          api.getDecisionSupportSummary().catch(() => null),
        ]);

        if (incs.status === 'fulfilled') setIncidents(incs.value);
        if (rules.status === 'fulfilled') setPriorityRules(rules.value);
        if (preds.status === 'fulfilled') setPredictions(preds.value);
        if (know.status === 'fulfilled') setKnowledge(know.value);
        if (dec.status === 'fulfilled') setDecisionSupport(dec.value);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };
    fetchPageData();
  }, []);

  const fetchIncidentDetail = useCallback(async (incident: Incident) => {
    try {
      setDetailLoading(true);
      setError(null);
      const data = await api.getClusterDetail(incident.id).catch(() => null);
      setDetail(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load incident detail');
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleCardClick = async (incident: Incident) => {
    setSelectedIncident(incident);
    setWorkspaceOpen(true);
    await fetchIncidentDetail(incident);
  };

  const closeWorkspace = () => {
    setWorkspaceOpen(false);
    setSelectedIncident(null);
    setDetail(null);
  };

  const wards = useMemo(() => {
    const set = new Set<string>();
    incidents.forEach(i => { if (i.ward) set.add(i.ward); });
    return Array.from(set).sort();
  }, [incidents]);

  const statuses = useMemo(() => {
    const set = new Set<string>();
    incidents.forEach(i => { if (i.status) set.add(i.status); });
    return Array.from(set).sort();
  }, [incidents]);

  const filteredIncidents = useMemo(() => {
    let data = [...incidents];
    if (search.trim()) {
      const q = search.toLowerCase();
      data = data.filter(i =>
        i.incident_number.toLowerCase().includes(q) ||
        i.category?.toLowerCase().includes(q) ||
        i.ward?.toLowerCase().includes(q) ||
        i.summary?.toLowerCase().includes(q) ||
        (i.status || '').toLowerCase().includes(q)
      );
    }
    if (filterPriority !== 'all') {
      data = data.filter(i => (i.priority_label || '').toLowerCase() === filterPriority.toLowerCase());
    }
    if (filterStatus !== 'all') {
      data = data.filter(i => i.status === filterStatus);
    }
    if (filterWard !== 'all') {
      data = data.filter(i => i.ward === filterWard);
    }
    data.sort((a, b) => {
      let va: any = (a as any)[sortField];
      let vb: any = (b as any)[sortField];
      if (typeof va === 'string') va = va.toLowerCase();
      if (typeof vb === 'string') vb = vb.toLowerCase();
      if (va == null) va = '';
      if (vb == null) vb = '';
      if (typeof va === 'number' && typeof vb === 'number') {
        return sortDir === 'asc' ? va - vb : vb - va;
      }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return data;
  }, [incidents, search, filterPriority, filterStatus, filterWard, sortField, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filteredIncidents.length / ITEMS_PER_PAGE));
  const safePage = Math.min(currentPage, totalPages);
  const pageItems = useMemo(() => {
    const start = (safePage - 1) * ITEMS_PER_PAGE;
    return filteredIncidents.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredIncidents, safePage]);

  useEffect(() => { setCurrentPage(1); }, [search, filterPriority, filterStatus, filterWard, sortField, sortDir]);

  const selectedComplaints: Complaint[] = detail?.complaints ?? selectedIncident?.complaints ?? [];
  const selectedPriorityHistory: PriorityHistory[] = detail?.priority_history ?? selectedIncident?.priority_history ?? [];
  const selectedSummary = detail?.summary || selectedIncident?.summary || INITIAL_SUMMARY;
  const selectedStatus = detail?.status || selectedIncident?.status || 'Open';
  const selectedClusterSize = detail?.cluster_size ?? selectedIncident?.cluster_size ?? 0;
  const selectedPriority = detail?.priority_label || selectedIncident?.priority_label || 'Medium';
  const selectedPriorityScore = detail?.priority_score ?? selectedIncident?.priority_score ?? 50;
  const selectedWard = detail?.ward || selectedIncident?.ward || 'Unknown';
  const selectedCategory = detail?.category || selectedIncident?.category || 'General';
  const selectedDaysOpen = detail?.days_open ?? selectedIncident?.days_open ?? 0;
  const selectedRecommended = detail?.recommended_action || selectedIncident?.recommended_action || DEFAULT_RECOMMENDATION;

  const avgSimilarity = selectedComplaints.length > 0
    ? selectedComplaints.reduce((sum, c) => sum + (c.similarity_score || 0), 0) / selectedComplaints.length
    : 0;

  const aiSummaryText = detail?.ai_summary
    || detail?.reasoning_summary
    || predictions?.summary
    || knowledge?.summary
    || decisionSupport?.summary
    || INITIAL_SUMMARY;

  const rootCause = detail?.root_cause
    || selectedComplaints[0]?.text
    || 'Review linked complaints for root cause analysis.';

  const escalationRisk = detail?.escalation_risk
    ?? detail?.escalationProbability
    ?? predictions?.risks?.find((r: any) => r.category === selectedCategory)?.confidence
    ?? selectedPriorityScore;

  const relatedKnowledge = detail?.knowledge_insights
    || knowledge?.insights
    || predictions?.risks
    || [];

  const recs = detail?.recommendations
    || detail?.decision_recommendations
    || decisionSupport?.recommendations
    || [];

  const resources = detail?.resources
    || detail?.resource_allocation
    || decisionSupport?.resourceAllocation
    || [];

  const responsibleDepartment = detail?.responsible_department
    || detail?.department
    || selectedCategory;

  const priorityExplanation = detail?.priority_explanation
    || detail?.priority_reasoning
    || (priorityRules && priorityRules.length > 0
      ? `Priority calculated from ${priorityRules.length} active AI weighting rules. Score: ${selectedPriorityScore}.`
      : `AI priority score of ${selectedPriorityScore} derived from cluster size (${selectedClusterSize}), days open (${selectedDaysOpen}d), complaint volume, and historical severity trends.`);

  const renderInvestigationCard = (inc: Incident) => {
    const color = getPriorityColor(inc.priority_label);
    return (
      <div
        key={inc.id}
        className="investigation-card"
        onClick={() => handleCardClick(inc)}
        style={{ borderLeft: `3px solid ${color}` }}
      >
        <div className="inc-card-top">
          <span className="inc-card-number">{inc.incident_number}</span>
          <PriorityBadge priority={inc.priority_label} />
        </div>
        <div className="inc-card-body">
          <h4 className="inc-card-title">{inc.category}</h4>
          <div className="inc-card-meta">
            <span><MapPin size={12} />{inc.ward}</span>
            <span><Clock size={12} />{inc.days_open}d open</span>
            <span><GitBranch size={12} />{inc.cluster_size} reports</span>
          </div>
          <p className="inc-card-summary">{inc.summary?.substring(0, 160)}{inc.summary?.length > 160 ? '…' : ''}</p>
          {inc.recommended_action && (
            <div className="inc-card-rec"><Lightbulb size={12} />{inc.recommended_action}</div>
          )}
          <div className="inc-card-footer">
            <span className="inc-card-status" data-status={inc.status?.toLowerCase()}>
              <CheckCircle2 size={12} />{inc.status || 'Open'}
            </span>
            <span className="inc-card-score">Score: {inc.priority_score}</span>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="ice-page">
        <Header title="AI Cluster Intelligence Explorer" subtitle="Initializing investigation workspace" />
        <div className="loading-state">
          <Loader2 size={48} className="spin" />
          <p>Loading incident intelligence feeds...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="ice-page">
      <Header title="AI Cluster Intelligence Explorer" subtitle="Incident Investigation Center — Real-time AI-Powered Analysis" />

      {error && (
        <div className="global-banner warning">
          <AlertTriangle size={16} />{error}
        </div>
      )}

      {/* Controls Bar */}
      <div className="controls-card glass-card">
        <div className="controls-row">
          <div className="search-wrap">
            <Search size={16} />
            <input
              type="text"
              placeholder="Search incidents, wards, categories..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="filter-wrap">
            <Filter size={14} />
            <select value={filterPriority} onChange={e => setFilterPriority(e.target.value as any)}>
              <option value="all">All Priorities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
            <option value="all">All Statuses</option>
            {statuses.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={filterWard} onChange={e => setFilterWard(e.target.value)}>
            <option value="all">All Wards</option>
            {wards.map(w => <option key={w} value={w}>{w}</option>)}
          </select>
          <div className="sort-wrap">
            <SortAsc size={14} />
            <select value={sortField} onChange={e => setSortField(e.target.value as SortField)}>
              <option value="priority_score">Priority</option>
              <option value="cluster_size">Cluster Size</option>
              <option value="days_open">Days Open</option>
              <option value="incident_number">Number</option>
              <option value="ward">Ward</option>
            </select>
            <button
              className="sort-dir-btn"
              onClick={() => setSortDir(d => d === 'asc' ? 'desc' : 'asc')}
              title={sortDir === 'asc' ? 'Ascending' : 'Descending'}
            >
              {sortDir === 'asc' ? '↑' : '↓'}
            </button>
          </div>
        </div>
        <div className="results-info">
          <span>{filteredIncidents.length} incident{filteredIncidents.length !== 1 ? 's' : ''} found</span>
        </div>
      </div>

      {/* Investigation Cards */}
      {pageItems.length > 0 ? (
        <>
          <div className="investigation-grid">
            {pageItems.map(renderInvestigationCard)}
          </div>
          {totalPages > 1 && (
            <div className="pagination-bar">
              <button
                className="page-btn"
                disabled={safePage <= 1}
                onClick={() => setCurrentPage(p => p - 1)}
              >
                <ChevronLeft size={16} /> Prev
              </button>
              <span className="page-indicator">
                Page {safePage} of {totalPages}
              </span>
              <button
                className="page-btn"
                disabled={safePage >= totalPages}
                onClick={() => setCurrentPage(p => p + 1)}
              >
                Next <ChevronRight size={16} />
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="empty-state">
          <Search size={32} />
          <p>No incidents match your search criteria.</p>
          <button className="retry-btn" onClick={() => { setSearch(''); setFilterPriority('all'); setFilterStatus('all'); setFilterWard('all'); }}>Clear Filters</button>
        </div>
      )}

      {/* Investigation Workspace */}
      {workspaceOpen && selectedIncident && (
        <div className="workspace-overlay">
          <div className="workspace-backdrop" onClick={closeWorkspace} />
          <div className="workspace-panel">
            <div className="workspace-header">
              <div className="workspace-title-group">
                <button className="back-btn" onClick={closeWorkspace}><X size={18} /></button>
                <div>
                  <h2>{selectedIncident.incident_number} Investigation</h2>
                  <span className="workspace-subtitle">{selectedCategory} · {selectedWard}</span>
                </div>
              </div>
              <div className="workspace-header-right">
                <PriorityBadge priority={selectedPriority} />
                <span className="ws-days-open"><Clock size={14} />{selectedDaysOpen}d open</span>
              </div>
            </div>

            {detailLoading && (
              <div className="loading-state inline">
                <Loader2 size={24} className="spin" />
                <p>Loading incident intelligence...</p>
              </div>
            )}

            {!detailLoading && (
              <div className="workspace-content">
                <div className="workspace-left">
                  {/* Incident Summary */}
                  <SectionCard
                    title="Incident Summary"
                    subtitle="AI-generated overview"
                    icon={<Brain size={18} />}
                    accent={getPriorityColor(selectedPriority)}
                  >
                    <p className="summary-text">{selectedSummary}</p>
                    <div className="summary-meta-row">
                      <span className="meta-chip"><MapPin size={12} />{selectedWard}</span>
                      <span className="meta-chip"><Users size={12} />{selectedClusterSize} linked reports</span>
                      <span className="meta-chip"><Clock size={12} />{selectedDaysOpen} days open</span>
                    </div>
                  </SectionCard>

                  {/* Root Cause Analysis */}
                  <SectionCard title="Root Cause Analysis" icon={<Target size={18} />}>
                    <div className="root-cause-content">
                      <p className="root-cause-text">{rootCause}</p>
                      {selectedComplaints.length > 0 && (
                        <div className="top-complaints">
                          <h5>Top Contributing Complaints</h5>
                          {selectedComplaints.slice(0, 3).map((c, i) => (
                            <div key={c.id} className="top-complaint-row">
                              <span className="tc-rank">#{i + 1}</span>
                              <span className="tc-text">{c.text}</span>
                              <span className="tc-similarity">{Math.round((c.similarity_score || 0) * 100)}%</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </SectionCard>

                  {/* AI Priority Explanation */}
                  <SectionCard title="AI Priority Explanation" subtitle="How priority was determined" icon={<Zap size={18} />}>
                    <div className="priority-explainer">
                      <div className="priority-score-display">
                        <div className="score-ring">
                          <svg viewBox="0 0 80 80">
                            <circle cx="40" cy="40" r="34" fill="none" stroke="#e2e8f0" strokeWidth="7" />
                            <circle
                              cx="40" cy="40" r="34"
                              fill="none"
                              stroke={getPriorityColor(selectedPriority)}
                              strokeWidth="7"
                              strokeDasharray={`${selectedPriorityScore * 2.13}, 213`}
                              strokeLinecap="round"
                              transform="rotate(-90 40 40)"
                            />
                            <text x="40" y="37" textAnchor="middle" fontSize="18" fontWeight="800" fill={getPriorityColor(selectedPriority)}>{selectedPriorityScore}</text>
                            <text x="40" y="52" textAnchor="middle" fontSize="10" fontWeight="600" fill={getPriorityColor(selectedPriority)}>Score</text>
                          </svg>
                        </div>
                        <PriorityBadge priority={selectedPriority} />
                      </div>
                      <p className="priority-explainer-text">{priorityExplanation}</p>
                      {(priorityRules || []).length > 0 && (
                        <div className="priority-rules-list">
                          {priorityRules.slice(0, 6).map((rule: PriorityRule) => (
                            <div key={rule.id} className="priority-rule-row">
                              <span className="rule-name">{rule.name || rule.description || 'Rule'}</span>
                              <span className="rule-weight">Weight: {rule.weight ?? '?'}%</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </SectionCard>

                  {/* Prediction & Escalation Risk */}
                  <SectionCard title="Predictions & Escalation Risk" subtitle="AI forward-looking analysis" icon={<Flame size={18} />}>
                    <div className="escalation-content">
                      <div className="escalation-meter">
                        <span className="escalation-label">Escalation Probability</span>
                        <div className="escalation-track">
                          <div
                            className="escalation-fill"
                            style={{ width: `${Math.min(escalationRisk, 100)}%` }}
                          />
                        </div>
                        <span className="escalation-value" style={{ color: escalationRisk > 70 ? '#dc2626' : escalationRisk > 40 ? '#ca8a04' : '#16a34a' }}>
                          {Math.round(escalationRisk)}%
                        </span>
                      </div>
                      <p className="escalation-text">
                        {predictions?.summary ||
                          `AI prediction indicates a ${Math.round(escalationRisk)}% chance of escalation within the next 7 days based on historical patterns.`}
                      </p>
                      {(predictions?.risks?.length ?? 0) > 0 && (
                        <div className="prediction-risks">
                          {(predictions!.risks ?? []).slice(0, 3).map((risk: any, i: number) => (
                            <div key={i} className="prediction-risk-row">
                              <AlertTriangle size={12} />
                              <span>{risk.reason || risk.description || 'Risk detected'}</span>
                              <span className="risk-conf">{risk.confidence ?? 75}%</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </SectionCard>

                  {/* Timeline */}
                  <SectionCard title="Complaint Relationship Timeline" subtitle={`${selectedComplaints.length} linked complaints`} icon={<Calendar size={18} />}>
                    {selectedComplaints.length > 0 ? (
                      <div className="complaint-timeline">
                        {[...selectedComplaints]
                          .sort((a, b) => new Date(a.date_received).getTime() - new Date(b.date_received).getTime())
                          .map((c, i) => (
                            <div key={c.id} className="timeline-item">
                              <div className="tl-marker">
                                <span className="tl-dot" />
                                <span className="tl-line" />
                              </div>
                              <div className="tl-content">
                                <div className="tl-top">
                                  <span className="tl-comp">{c.complaint_number}</span>
                                  <span className="tl-date">{new Date(c.date_received).toLocaleDateString('en-IN')}</span>
                                  <span className="tl-score">Similarity: {Math.round((c.similarity_score || 0) * 100)}%</span>
                                </div>
                                <p className="tl-text">{c.text}</p>
                                {c.merge_reason && <span className="tl-merge-reason">{c.merge_reason}</span>}
                              </div>
                            </div>
                          ))}
                      </div>
                    ) : (
                      <div className="empty-inline">No complaints linked for timeline.</div>
                    )}
                  </SectionCard>
                </div>

                <div className="workspace-right">
                  {/* Status & Priority Timeline */}
                  <SectionCard title="Incident Status" icon={<ShieldAlert size={18} />}>
                    <div className={`status-display status-${(selectedStatus || 'open').toLowerCase()}`}>
                      <span className="status-dot" />
                      <span className="status-text">{selectedStatus || 'Open'}</span>
                    </div>
                    <div className="priority-timeline-mini">
                      {(selectedPriorityHistory || []).length > 0 ? (
                        selectedPriorityHistory.map((ph: PriorityHistory) => (
                          <div key={ph.id} className="ph-row">
                            <span className="ph-score">{ph.old_score} → {ph.new_score}</span>
                            <span className="ph-reason">{ph.reason}</span>
                            <span className="ph-date">{new Date(ph.changed_at).toLocaleDateString('en-IN')}</span>
                          </div>
                        ))
                      ) : (
                        <div className="empty-inline">No priority history recorded.</div>
                      )}
                    </div>
                  </SectionCard>

                  {/* Responsible Department & Resource Allocation */}
                  <SectionCard title="Responsible Department" subtitle="AI-suggested allocation" icon={<Building2 size={18} />}>
                    <div className="dept-allocation">
                      <div className="dept-primary">
                        <span className="dept-icon-wrap"><Wrench size={18} /></span>
                        <span className="dept-name">{responsibleDepartment}</span>
                      </div>
                      {resources.length > 0 ? (
                        <div className="resource-recs">
                          {resources.slice(0, 4).map((res: any, i: number) => (
                            <div key={i} className="res-row">
                              <span className="res-label">{res.department || res.name || 'Resource'}</span>
                              <div className="res-bars">
                                <span className="res-val current">{res.current ?? res.current_teams ?? 5}</span>
                                <ChevronRight size={10} />
                                <span className="res-val recommended">{res.recommended ?? res.recommended_teams ?? 8}</span>
                              </div>
                              <span className="res-improvement">+{res.improvement ?? res.improvement_percent ?? 15}%</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="empty-inline">AI recommends reviewing resource level based on cluster size and days open.</p>
                      )}
                    </div>
                  </SectionCard>

                  {/* Duplicate Count & Linked Complaints */}
                  <SectionCard title="Cluster Overview" icon={<GitBranch size={18} />}>
                    <div className="cluster-overview-grid">
                      <div className="co-item">
                        <span className="co-value">{selectedClusterSize}</span>
                        <span className="co-label">Duplicate Count</span>
                      </div>
                      <div className="co-item">
                        <span className="co-value">{selectedComplaints.length}</span>
                        <span className="co-label">Linked Complaints</span>
                      </div>
                      <div className="co-item">
                        <span className="co-value">{avgSimilarity > 0 ? `${Math.round(avgSimilarity * 100)}%` : '—'}</span>
                        <span className="co-label">Avg Similarity</span>
                      </div>
                      {selectedIncident?.days_open != null && (
                        <div className="co-item">
                          <span className="co-value">{selectedIncident.days_open}d</span>
                          <span className="co-label">Days Open</span>
                        </div>
                      )}
                    </div>
                    {selectedComplaints.length > 0 && (
                      <div className="linked-complaints">
                        <h5>Recent Complaints</h5>
                        {selectedComplaints.slice(0, 5).map(c => (
                          <div key={c.id} className="lc-row">
                            <span className="lc-num">{c.complaint_number}</span>
                            <span className="lc-text">{c.text?.substring(0, 60)}{c.text?.length > 60 ? '…' : ''}</span>
                            <span className="lc-sim">{Math.round((c.similarity_score || 0) * 100)}%</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </SectionCard>

                  {/* Knowledge Insights */}
                  <SectionCard title="Knowledge Insights" subtitle="Historical pattern intelligence" icon={<BookOpen size={18} />}>
                    {relatedKnowledge.length > 0 ? (
                      <div className="knowledge-list">
                        {relatedKnowledge.slice(0, 6).map((ki: any, i: number) => (
                          <div key={i} className="knowledge-row">
                            <span className="ki-category">{ki.category || ki.title || 'Insight'}</span>
                            <p className="ki-statement">{ki.statement || ki.reason || ki.description || 'No additional insight available.'}</p>
                            {ki.related_incidents != null && (
                              <span className="ki-related">{ki.related_incidents} related incidents</span>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-inline">
                        <p>{knowledge?.summary || 'No knowledge insights available for this incident category.'}</p>
                      </div>
                    )}
                  </SectionCard>

                  {/* Decision Recommendations */}
                  <SectionCard title="Decision Recommendations" subtitle="AI-suggested interventions" icon={<ArrowUpRight size={18} />}>
                    {recs.length > 0 ? (
                      <div className="recs-list">
                        {recs.slice(0, 6).map((rec: DecisionRecommendation, i: number) => (
                          <div key={i} className={`rec-row rec-${(rec.priority || 'medium').toLowerCase()}`}>
                            <div className="rec-row-top">
                              <span className="rec-idx">#{i + 1}</span>
                              <PriorityBadge priority={rec.priority} />
                            </div>
                            <h5>{rec.title}</h5>
                            <p>{rec.reason}</p>
                            <div className="rec-row-meta">
                              <span><Users size={12} />{rec.department}</span>
                              <span><Zap size={12} />{rec.confidence ?? 75}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-inline">
                        <p>{decisionSupport?.summary || 'No specific recommendations available at this time.'}</p>
                      </div>
                    )}
                  </SectionCard>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Clusters;
