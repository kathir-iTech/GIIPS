import { Link } from 'react-router-dom';
import { User, ShieldAlert, Play, LogIn, UserPlus, Building2, GitBranch, BarChart3, MapPin, Cpu, LogOut, LayoutDashboard, Database, Copy, Check } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useState } from 'react';
import './Landing.css';

const DEMO_ACCOUNTS = [
  { role: 'Executive', email: 'collector@giips.gov.in', password: 'password123', icon: Building2, color: '#a78bfa' },
  { role: 'Officer', email: 'officer1@giips.gov.in', password: 'password123', icon: ShieldAlert, color: '#34d399' },
  { role: 'Officer', email: 'officer2@giips.gov.in', password: 'password123', icon: ShieldAlert, color: '#34d399' },
  { role: 'Officer', email: 'officer3@giips.gov.in', password: 'password123', icon: ShieldAlert, color: '#34d399' },
  { role: 'Citizen', email: 'citizen@giips.gov.in', password: 'password123', icon: User, color: '#60a5fa' },
];

const Landing = () => {
  const { user, logout } = useAuth();
  const [copied, setCopied] = useState<string | null>(null);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(text);
    setTimeout(() => setCopied(null), 2000);
  };

  const dashboardPath = user?.role === 'Citizen' ? '/citizen'
    : user?.role === 'Officer' ? '/officer'
    : user?.role === 'Executive' ? '/executive'
    : null;

  return (
    <div className="landing-os">
      <div className="ambient-blobs">
        <div className="blob blob-1"></div>
        <div className="blob blob-2"></div>
        <div className="blob blob-3"></div>
      </div>

      <nav className="glass-nav">
        <div className="brand">GIIPS <span>OS</span></div>
        <div className="nav-links">
          <Link to="/citizen-services" className="nav-link">Citizen Services</Link>
          <Link to="/government-portal" className="nav-link">Government Portal</Link>
          <Link to="/demo" className="nav-link">Demo</Link>
          {user ? (
            <>
              <Link to={dashboardPath!} className="nav-link btn-dashboard">
                <LayoutDashboard size={16} /> Dashboard
              </Link>
              <button onClick={logout} className="nav-link btn-logout">
                <LogOut size={16} /> Sign Out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="nav-link btn-login">
                <LogIn size={16} /> Sign In
              </Link>
              <Link to="/register" className="nav-link btn-signup">
                <UserPlus size={16} /> Sign Up
              </Link>
            </>
          )}
        </div>
      </nav>

      <header className="hero-os">
        <div className="badge">Government Intelligence Powered by AI</div>
        <h1>Governance Intelligence & Prioritization System</h1>
        <p>AI-powered grievance clustering, priority scoring, and decision intelligence for municipal governance.</p>
        <div className="hero-actions">
          <Link to="/citizen-services" className="btn-main">
            <User size={20} /> Citizen Portal
          </Link>
          <Link to="/government-portal" className="btn-main btn-secondary">
            <ShieldAlert size={20} /> Government Login
          </Link>
          <Link to="/demo" className="btn-demo">
            <Play size={20} /> Live Demo
          </Link>
        </div>
      </header>

      <section className="role-cards">
        <div className="role-card glass-card">
          <div className="role-icon citizen"><User size={32} /></div>
          <h3>Citizen</h3>
          <p>Submit grievances, track AI-powered classifications, and monitor resolution progress in real time.</p>
          <div className="role-actions">
            {user?.role === 'Citizen' ? (
              <Link to="/citizen" className="btn-role"><LayoutDashboard size={16} /> My Dashboard</Link>
            ) : (
              <>
                <Link to="/register" className="btn-role"><UserPlus size={16} /> Register</Link>
                <Link to="/login" className="btn-role secondary"><LogIn size={16} /> Login</Link>
              </>
            )}
          </div>
        </div>
        <div className="role-card glass-card">
          <div className="role-icon officer"><ShieldAlert size={32} /></div>
          <h3>Officer</h3>
          <p>View prioritized incidents, investigate AI-clustered complaints, and manage resolution workflows.</p>
          <div className="role-actions">
            {user?.role === 'Officer' ? (
              <Link to="/officer" className="btn-role"><LayoutDashboard size={16} /> My Dashboard</Link>
            ) : (
              <Link to="/login" className="btn-role"><LogIn size={16} /> Login</Link>
            )}
          </div>
        </div>
        <div className="role-card glass-card">
          <div className="role-icon executive"><Building2 size={32} /></div>
          <h3>Executive</h3>
          <p>District-level command center with AI-driven insights, department analytics, and governance copilot.</p>
          <div className="role-actions">
            {user?.role === 'Executive' ? (
              <Link to="/executive" className="btn-role"><LayoutDashboard size={16} /> My Dashboard</Link>
            ) : (
              <Link to="/login" className="btn-role"><LogIn size={16} /> Login</Link>
            )}
          </div>
        </div>
      </section>

      <section className="demo-section">
        <div className="demo-header">
          <Database size={28} className="demo-section-icon" />
          <h2>Demo Credentials</h2>
          <p>Use these pre-seeded accounts to explore each role. The same password works for all: <strong>password123</strong></p>
        </div>
        <div className="demo-table-wrapper">
          <table className="demo-table">
            <thead>
              <tr>
                <th>Role</th>
                <th>Email</th>
                <th>Password</th>
                <th>Can Access</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {DEMO_ACCOUNTS.map((acc) => {
                const Icon = acc.icon;
                const portal = acc.role === 'Citizen' ? 'Citizen Portal / My Complaints'
                  : acc.role === 'Officer' ? 'Officer Dashboard / Incident Feed / Analysis / Clusters / Spatial'
                  : 'Executive Dashboard / Admin Panel / All Officer areas';
                return (
                  <tr key={acc.email}>
                    <td>
                      <span className="demo-role-badge" style={{ borderColor: acc.color, color: acc.color }}>
                        <Icon size={14} /> {acc.role}
                      </span>
                    </td>
                    <td className="demo-email">{acc.email}</td>
                    <td className="demo-pw">{acc.password}</td>
                    <td className="demo-access">{portal}</td>
                    <td>
                      <button
                        className="demo-copy-btn"
                        onClick={() => handleCopy(acc.email)}
                        title="Copy email"
                      >
                        {copied === acc.email ? <Check size={14} /> : <Copy size={14} />}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="demo-note">
          <strong>How to test:</strong> Click <Link to="/login">Sign In</Link>, paste an email above, enter <code>password123</code>, and you will be routed to the correct dashboard for that role. Each role sees only its own pages — a Citizen cannot access officer or executive routes.
        </p>
      </section>

      <section className="features-section">
        <h2>Key Capabilities</h2>
        <div className="features-grid">
          <div className="feature-card glass-card">
            <GitBranch size={24} className="feature-icon" />
            <h3>AI Clustering</h3>
            <p>Automatically groups duplicate complaints using semantic NLP, reducing workload by up to 85%.</p>
          </div>
          <div className="feature-card glass-card">
            <BarChart3 size={24} className="feature-icon" />
            <h3>Priority Scoring</h3>
            <p>Multi-factor AI scoring assigns Critical/High/Medium/Low priority to every incident.</p>
          </div>
          <div className="feature-card glass-card">
            <MapPin size={24} className="feature-icon" />
            <h3>Spatial Intelligence</h3>
            <p>GIS heatmaps, hotspot detection, and resource simulation across Tamil Nadu districts.</p>
          </div>
          <div className="feature-card glass-card">
            <Cpu size={24} className="feature-icon" />
            <h3>Decision Engine</h3>
            <p>Executive copilot, predictive escalation alerts, and AI-recommended resource allocation.</p>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="footer-brand">GIIPS — Governance Incident Intelligence & Prioritization System</div>
        <div className="footer-links">
          <Link to="/methodology">Methodology</Link>
          <Link to="/demo">Demo</Link>
          <Link to="/citizen-services">Citizen Services</Link>
        </div>
        <div className="footer-copy">Tamil Nadu Municipal Governance Platform</div>
      </footer>
    </div>
  );
};

export default Landing;