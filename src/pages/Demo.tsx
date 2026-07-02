import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert, Users, FileText, Cpu, GitBranch, Gauge,
  CheckCircle, LayoutDashboard, BarChart3, Lightbulb,
  PhoneCall, Play, Pause, RotateCcw, ChevronLeft, ChevronRight
} from 'lucide-react';
import './Demo.css';

type Step = {
  id: string;
  title: string;
  description: string;
  icon: React.ElementType;
  color: string;
  duration: number;
  mockup?: string;
};

const STEPS: Step[] = [
  {
    id: 'welcome',
    title: 'Welcome to GIIPS',
    description: 'Governance Incident Intelligence & Prioritization System — transforming thousands of complaints into actionable intelligence for smarter municipal governance.',
    icon: ShieldAlert,
    color: '#3b82f6',
    duration: 3000,
  },
  {
    id: 'citizen',
    title: 'Citizen Registers & Logs In',
    description: 'A citizen creates an account and logs into the GIIPS portal to submit a grievance about potholes near the main market in Ward 4, Coimbatore.',
    icon: Users,
    color: '#3b82f6',
    duration: 3000,
    mockup: 'login',
  },
  {
    id: 'submit',
    title: 'Submit Complaint',
    description: 'The citizen fills in the complaint wizard: title, detailed description, location, and ward number. The form validates before submission.',
    icon: FileText,
    color: '#6366f1',
    duration: 3000,
    mockup: 'form',
  },
  {
    id: 'classification',
    title: 'AI Classification Animation',
    description: 'The NLP engine analyses the complaint text in real-time. Predicted category: "Road Infrastructure" with 93% confidence.',
    icon: Cpu,
    color: '#8b5cf6',
    duration: 3500,
    mockup: 'classification',
  },
  {
    id: 'clustering',
    title: 'Duplicate Detection Animation',
    description: 'Semantic clustering identifies 14 similar complaints already filed in the same ward. They are automatically merged into a single incident.',
    icon: GitBranch,
    color: '#06b6d4',
    duration: 3500,
    mockup: 'clustering',
  },
  {
    id: 'priority',
    title: 'Priority Score Animation',
    description: 'The priority engine calculates a score of 87/100 and labels the incident High, based on severity, cluster size, and days open.',
    icon: Gauge,
    color: '#f59e0b',
    duration: 3500,
    mockup: 'priority',
  },
  {
    id: 'incident',
    title: 'Incident Created',
    description: 'A new incident INC-2024-A7F2 is generated and queued for the Roads Department. The citizen receives a confirmation with the reference number.',
    icon: CheckCircle,
    color: '#22c55e',
    duration: 2800,
    mockup: 'success',
  },
  {
    id: 'officer',
    title: 'Officer Dashboard — New Incident Highlighted',
    description: 'The officer\'s dashboard immediately highlights the new High-priority incident in the Incident Feed and the KPI grid updates live.',
    icon: LayoutDashboard,
    color: '#3b82f6',
    duration: 3200,
    mockup: 'dashboard',
  },
  {
    id: 'cluster-intel',
    title: 'Cluster Intelligence — Investigation Opens',
    description: 'One click opens the investigation workspace: root-cause analysis, linked complaints timeline, and priority explanation with active weighting rules.',
    icon: ShieldAlert,
    color: '#ef4444',
    duration: 3500,
    mockup: 'cluster',
  },
  {
    id: 'spatial',
    title: 'Spatial Intelligence — Zooms to District',
    description: 'The GIS map zooms to Coimbatore district. Hotspots, risk analysis layers, and resource simulation are one click away.',
    icon: ShieldAlert,
    color: '#10b981',
    duration: 3000,
    mockup: 'spatial',
  },
  {
    id: 'executive',
    title: 'Executive Dashboard — KPIs Update Live',
    description: 'The Collector sees live KPI cards across all departments, district health rankings, and emerging risk forecasts updated in real time.',
    icon: BarChart3,
    color: '#6366f1',
    duration: 3200,
    mockup: 'executive',
  },
  {
    id: 'recommendations',
    title: 'AI Recommendation Appears',
    description: 'The Decision Engine recommends deploying 2 additional maintenance crews to Ward 4 within the next 7 days to address the backlog.',
    icon: Lightbulb,
    color: '#f59e0b',
    duration: 3000,
    mockup: 'recommendations',
  },
  {
    id: 'decision',
    title: 'Collector Decision Card',
    description: 'With one click the District Collector approves the resource plan. The system logs the decision and notifies the Roads Department immediately.',
    icon: PhoneCall,
    color: '#22c55e',
    duration: 3200,
    mockup: 'decision',
  },
];

const SPRING = { type: 'spring' as const, stiffness: 280, damping: 28 };

const slideVariants = {
  enter: (dir: number) => ({
    x: dir > 0 ? 420 : -420,
    opacity: 0,
    scale: 0.96,
  }),
  center: {
    x: 0,
    opacity: 1,
    scale: 1,
  },
  exit: (dir: number) => ({
    x: dir < 0 ? 420 : -420,
    opacity: 0,
    scale: 0.96,
  }),
};

const ClassificationMockup = ({ color }: { color: string }) => (
  <div className="mockup-browser">
    <div className="mockup-bar">
      <span className="mockup-title">AI Classification</span>
      <div className="mockup-dots"><span /><span /><span /></div>
    </div>
    <div className="mockup-body">
      {[
        { label: 'Roads', pct: 93 },
        { label: 'Water', pct: 4 },
        { label: 'Drainage', pct: 2 },
        { label: 'Other', pct: 1 },
      ].map((item, i) => (
        <div key={item.label} className="mockup-row">
          <span className="mockup-lbl">{item.label}</span>
          <div className="mockup-track">
            <motion.div
              className="mockup-fill"
              initial={{ width: 0 }}
              animate={{ width: `${item.pct}%` }}
              transition={{ delay: 0.3 + i * 0.2, duration: 1.2, ease: 'easeOut' }}
              style={{ backgroundColor: i === 0 ? color : '#64748b' }}
            />
          </div>
          <span className="mockup-pct">{item.pct}%</span>
        </div>
      ))}
    </div>
  </div>
);

const ClusteringMockup = ({ color }: { color: string }) => (
  <div className="mockup-browser">
    <div className="mockup-bar">
      <span className="mockup-title">Duplicate Detection</span>
      <div className="mockup-dots"><span /><span /><span /></div>
    </div>
    <div className="mockup-body cluster-body">
      {Array.from({ length: 8 }).map((_, i) => {
        const isCluster = i < 5;
        const cx = isCluster ? 30 + (i % 3) * 18 : 55 + (i - 5) * 12;
        const cy = isCluster ? 35 + Math.floor(i / 3) * 22 : 50 + (i - 5) * 15;
        return (
          <motion.div
            key={i}
            className="cluster-dot"
            initial={{ x: 0, y: 0, opacity: 0 }}
            animate={{
              x: cx - 50,
              y: cy - 50,
              opacity: 1,
              backgroundColor: isCluster ? color : '#64748b',
            }}
            transition={{ delay: 0.3 + i * 0.15, type: 'spring', stiffness: 200, damping: 20 }}
          />
        );
      })}
      {[0, 1, 2, 3, 4].map(i => (
        <svg key={`line-${i}`} className="cluster-lines" viewBox="0 0 100 100" preserveAspectRatio="none">
          <motion.line
            x1={30 + (i % 3) * 18} y1={35 + Math.floor(i / 3) * 22}
            x2={30 + ((i + 1) % 3) * 18} y2={35 + Math.floor((i + 1) / 3) * 22}
            stroke={color}
            strokeWidth="0.8"
            strokeOpacity="0.5"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ delay: 0.8 + i * 0.1, duration: 0.5 }}
          />
        </svg>
      ))}
    </div>
  </div>
);

const PriorityMockup = ({ color }: { color: string }) => {
  const [score, setScore] = useState(0);
  useEffect(() => {
    const start = performance.now();
    const animate = (now: number) => {
      const progress = Math.min((now - start) / 1500, 1);
      setScore(Math.round(progress * 87));
      if (progress < 1) requestAnimationFrame(animate);
    };
    const raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, []);

  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const dashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="mockup-browser">
      <div className="mockup-bar">
        <span className="mockup-title">Priority Score</span>
        <div className="mockup-dots"><span /><span /><span /></div>
      </div>
      <div className="mockup-body priority-body">
        <svg viewBox="0 0 100 100" className="priority-gauge">
          <circle cx="50" cy="50" r={radius} fill="none" stroke="#1e293b" strokeWidth="8" />
          <motion.circle
            cx="50" cy="50" r={radius}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeDasharray={circumference}
            animate={{ strokeDashoffset: dashoffset }}
            transition={{ duration: 1.5, ease: 'easeOut' }}
            strokeLinecap="round"
            transform="rotate(-90 50 50)"
          />
          <text x="50" y="46" textAnchor="middle" fontSize="18" fontWeight="800" fill="white">{score}</text>
          <text x="50" y="60" textAnchor="middle" fontSize="8" fill="#94a3b8">/ 100</text>
        </svg>
        <motion.div
          className="priority-label"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.4 }}
        >
          <span className="p-badge" style={{ backgroundColor: `${color}20`, color }}>HIGH PRIORITY</span>
        </motion.div>
      </div>
    </div>
  );
};

const DashboardMockup = ({ color }: { color: string }) => (
  <div className="mockup-browser">
    <div className="mockup-bar">
      <span className="mockup-title">Officer Dashboard</span>
      <div className="mockup-dots"><span /><span /><span /></div>
    </div>
    <div className="mockup-body dash-body">
      {['Critical', 'High', 'Medium', 'Low'].map((label, i) => {
        const value = i === 1 ? 'NEW' : ['4', '12', '8', '22'][i];
        const localColor = i === 1 ? color : '#64748b';
        return (
          <motion.div
            key={label}
            className={`dash-card ${i === 1 ? 'highlighted' : ''}`}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 + i * 0.15 }}
            style={i === 1 ? { borderColor: color, boxShadow: `0 0 20px ${color}25` } : {}}
          >
            <span className="dash-label">{label}</span>
            <span className="dash-value" style={{ color: localColor }}>{value}</span>
          </motion.div>
        );
      })}
    </div>
  </div>
);

const ClusterMockup = ({ color }: { color: string }) => (
  <div className="mockup-browser">
    <div className="mockup-bar">
      <span className="mockup-title">Cluster Intelligence</span>
      <div className="mockup-dots"><span /><span /><span /></div>
    </div>
    <div className="mockup-body cluster-ws">
      <motion.div className="ws-card" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
        <div className="ws-header">
          <span>INC-2024-A7F2 Investigation</span>
          <span className="ws-badge" style={{ backgroundColor: `${color}20`, color }}>HIGH</span>
        </div>
        <div className="ws-meta">
          <span>Coimbatore · Ward 4</span>
          <span>14 linked reports</span>
        </div>
        <motion.div className="ws-timeline" initial={{ scaleY: 0 }} animate={{ scaleY: 1 }} transition={{ delay: 0.8, duration: 0.5 }} style={{ transformOrigin: 'top' }}>
          {['Submitted', 'Classified', 'Clustered', 'Prioritised'].map((label, i) => (
            <div key={label} className="ws-tl-item">
              <span className="ws-tl-dot" style={{ backgroundColor: i === 3 ? color : '#334155' }} />
              <span>{label}</span>
            </div>
          ))}
        </motion.div>
      </motion.div>
    </div>
  </div>
);

const SpatialMockup = ({ color }: { color: string }) => (
  <div className="mockup-browser">
    <div className="mockup-bar">
      <span className="mockup-title">Spatial Intelligence</span>
      <div className="mockup-dots"><span /><span /><span /></div>
    </div>
    <div className="mockup-body spatial-body">
      <div className="map-grid">
        {Array.from({ length: 9 }).map((_, i) => (
          <div key={i} className="map-cell" />
        ))}
        <motion.div
          className="map-pin"
          animate={{ y: [0, -6, 0], boxShadow: [`0 0 0 ${color}00`, `0 0 0 10px ${color}15`, `0 0 0 ${color}00`] }}
          transition={{ repeat: Infinity, duration: 2, delay: 0.5 }}
          style={{ backgroundColor: color, top: '30%', left: '55%' }}
        />
      </div>
      <motion.div className="map-tooltip" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
        <strong>Coimbatore</strong> — 14 complaints · 1 critical
      </motion.div>
    </div>
  </div>
);

const ExecutiveMockup = ({ color }: { color: string }) => (
  <div className="mockup-browser">
    <div className="mockup-bar">
      <span className="mockup-title">Executive Dashboard</span>
      <div className="mockup-dots"><span /><span /><span /></div>
    </div>
    <div className="mockup-body exec-body">
      {[
        { label: "Today's Complaints", value: '142', trend: '+5%' },
        { label: 'Critical Incidents', value: '7', trend: 'HIGH' },
        { label: 'Districts At Risk', value: '3', trend: '-3%' },
        { label: 'Avg Resolution', value: '2.4d', trend: '-10%' },
      ].map((item, i) => (
        <motion.div
          key={item.label}
          className="exec-card"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 + i * 0.15 }}
        >
          <span className="exec-label">{item.label}</span>
          <span className="exec-value" style={{ color }}>{item.value}</span>
          <span className="exec-trend">{item.trend}</span>
        </motion.div>
      ))}
    </div>
  </div>
);

const RecommendationsMockup = ({ color }: { color: string }) => (
  <div className="mockup-browser">
    <div className="mockup-bar">
      <span className="mockup-title">AI Recommendations</span>
      <div className="mockup-dots"><span /><span /><span /></div>
    </div>
    <div className="mockup-body rec-body">
      {[
        { title: 'Deploy 2 maintenance crews', dept: 'Roads', confidence: '93%' },
        { title: 'Pre-position drainage teams', dept: 'Drainage', confidence: '87%' },
      ].map((rec, i) => (
        <motion.div
          key={rec.title}
          className="rec-card"
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 + i * 0.25 }}
        >
          <span className="rec-idx">#{i + 1}</span>
          <div>
            <p className="rec-title">{rec.title}</p>
            <span className="rec-meta">{rec.dept} · {rec.confidence} confidence</span>
          </div>
        </motion.div>
      ))}
    </div>
  </div>
);

const DecisionMockup = ({ color }: { color: string }) => (
  <div className="mockup-browser">
    <div className="mockup-bar">
      <span className="mockup-title">Collector Decision</span>
      <div className="mockup-dots"><span /><span /><span /></div>
    </div>
    <div className="mockup-body decision-body">
      <motion.div
        className="decision-card"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <p className="decision-title">Approve Resource Plan</p>
        <p className="decision-desc">Deploy 2 additional maintenance crews to Ward 4, Coimbatore within 7 days.</p>
        <motion.button
          className="decision-approve"
          animate={{ boxShadow: [`0 0 0 0 ${color}00`, `0 0 0 8px ${color}25`, `0 0 0 0 ${color}00`] }}
          transition={{ repeat: Infinity, duration: 2 }}
          style={{ backgroundColor: color }}
        >
          Approve
        </motion.button>
      </motion.div>
    </div>
  </div>
);

const MockPreview = ({ type, color }: { type?: string; color: string }) => {
  if (!type) return null;
  if (type === 'classification') return <ClassificationMockup color={color} />;
  if (type === 'clustering') return <ClusteringMockup color={color} />;
  if (type === 'priority') return <PriorityMockup color={color} />;
  if (type === 'success') return <SuccessMockup color={color} />;
  if (type === 'dashboard') return <DashboardMockup color={color} />;
  if (type === 'cluster') return <ClusterMockup color={color} />;
  if (type === 'spatial') return <SpatialMockup color={color} />;
  if (type === 'executive') return <ExecutiveMockup color={color} />;
  if (type === 'recommendations') return <RecommendationsMockup color={color} />;
  if (type === 'decision') return <DecisionMockup color={color} />;
  return null;
};

const SuccessMockup = ({ color }: { color: string }) => (
  <div className="mockup-browser">
    <div className="mockup-bar">
      <span className="mockup-title">Confirmation</span>
      <div className="mockup-dots"><span /><span /><span /></div>
    </div>
    <div className="mockup-body success-body">
      <motion.div
        className="success-circle"
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.2 }}
      >
        <motion.svg
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ delay: 0.5, duration: 0.6 }}
          viewBox="0 0 24 24"
          fill="none"
          stroke="white"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="20 6 9 17 4 12" />
        </motion.svg>
      </motion.div>
      <motion.p
        className="success-text"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
      >
        Incident Created Successfully
      </motion.p>
      <motion.p
        className="success-ref"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2 }}
      >
        REF: INC-2024-A7F2
      </motion.p>
    </div>
  </div>
);

const LoginMockup = ({ color }: { color: string }) => (
  <div className="mockup-browser">
    <div className="mockup-bar">
      <span className="mockup-title">Login</span>
      <div className="mockup-dots"><span /><span /><span /></div>
    </div>
    <div className="mockup-body login-body">
      {['Email Address', 'Password'].map((label, i) => (
        <motion.div key={label} className="login-field" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 + i * 0.2 }}>
          <span className="login-label">{label}</span>
          <div className="login-track" />
        </motion.div>
      ))}
      <motion.button
        className="login-btn"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.9 }}
        style={{ backgroundColor: color }}
      >
        Sign In
      </motion.button>
    </div>
  </div>
);

const FormMockup = ({ color }: { color: string }) => (
  <div className="mockup-browser">
    <div className="mockup-bar">
      <span className="mockup-title">Submit Complaint</span>
      <div className="mockup-dots"><span /><span /><span /></div>
    </div>
    <div className="mockup-body form-body">
      {['Complaint Title', 'Description', 'Ward Number'].map((label, i) => (
        <motion.div key={label} className="form-field" initial={{ opacity: 0, width: 0 }} animate={{ opacity: 1, width: '100%' }} transition={{ delay: 0.3 + i * 0.2 }}>
          <span className="form-label">{label}</span>
          <div className="form-track" />
        </motion.div>
      ))}
    </div>
  </div>
);

const Demo = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [direction, setDirection] = useState(1);
  const [progress, setProgress] = useState(0);
  const navigate = useNavigate();

  const current = STEPS[currentStep];

  const goTo = useCallback((index: number) => {
    setDirection(index > currentStep ? 1 : -1);
    setCurrentStep(index);
    setProgress(0);
  }, [currentStep]);

  const togglePlay = useCallback(() => setIsPlaying(p => !p), []);

  const restart = useCallback(() => {
    setDirection(1);
    setCurrentStep(0);
    setProgress(0);
    setIsPlaying(true);
  }, []);

  useEffect(() => {
    if (!isPlaying) return;
    const stepDuration = current.duration;
    const interval = 50;
    const timer = setInterval(() => {
      setProgress(p => {
        const next = p + (interval / stepDuration) * 100;
        if (next >= 100) {
          clearInterval(timer);
          return 100;
        }
        return next;
      });
    }, interval);
    return () => clearInterval(timer);
  }, [isPlaying, currentStep, current.duration]);

  useEffect(() => {
    if (progress >= 100 && isPlaying) {
      const timer = setTimeout(() => {
        if (currentStep < STEPS.length - 1) {
          setDirection(1);
          setCurrentStep(s => s + 1);
          setProgress(0);
        } else {
          setIsPlaying(false);
        }
      }, 250);
      return () => clearTimeout(timer);
    }
  }, [progress, isPlaying, currentStep]);

  return (
    <div className="demo-mode">
      <header className="demo-header">
        <div className="demo-brand">
          <ShieldAlert size={22} color="#3b82f6" />
          <span className="demo-brand-text">GIIPS Demo</span>
          {isPlaying && <span className="live-dot" />}
        </div>
        <div className="demo-progress-track">
          <motion.div
            className="demo-progress-fill"
            animate={{ width: `${((currentStep + 1) / STEPS.length) * 100}%` }}
            transition={{ duration: 0.5, ease: 'easeInOut' }}
          />
        </div>
        <div className="demo-header-right">
          <span className="demo-step-label">Step {currentStep + 1} / {STEPS.length}</span>
          <button className="demo-exit" onClick={() => navigate('/')}>Exit Demo</button>
        </div>
      </header>

      <main className="demo-stage">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={current.id}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ ...SPRING, duration: 0.55 }}
            className="demo-panel"
          >
            <div className="demo-icon-ring" style={{ borderColor: `${current.color}40`, boxShadow: `0 0 50px ${current.color}25` }}>
              <current.icon size={44} color={current.color} />
            </div>
            <h2 className="demo-step-title">{current.title}</h2>
            <p className="demo-step-desc">{current.description}</p>

            <div className="demo-mockup">
              {current.mockup ? (
                <MockPreview type={current.mockup} color={current.color} />
              ) : (
                <div className="demo-mockup-empty">
                  <ShieldAlert size={40} color={current.color} />
                  <span>GIIPS Platform</span>
                </div>
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      </main>

      <footer className="demo-footer">
        <div className="demo-controls">
          <button
            className="demo-ctrl-btn"
            disabled={currentStep === 0}
            onClick={() => goTo(currentStep - 1)}
          >
            <ChevronLeft size={18} /> Prev
          </button>
          <button className="demo-ctrl-btn primary" onClick={togglePlay}>
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
            {isPlaying ? 'Pause' : 'Play'}
          </button>
          <button className="demo-ctrl-btn" onClick={restart}>
            <RotateCcw size={16} /> Restart
          </button>
          <button
            className="demo-ctrl-btn"
            disabled={currentStep === STEPS.length - 1}
            onClick={() => goTo(currentStep + 1)}
          >
            Next <ChevronRight size={18} />
          </button>
        </div>
        <div className="demo-dots">
          {STEPS.map((s, i) => (
            <button
              key={s.id}
              className={`demo-dot ${i === currentStep ? 'active' : i < currentStep ? 'done' : ''}`}
              onClick={() => goTo(i)}
              aria-label={`Go to step ${i + 1}: ${s.title}`}
              style={i === currentStep ? { backgroundColor: STEPS[currentStep].color } : {}}
            />
          ))}
        </div>
      </footer>
    </div>
  );
};

export default Demo;
