import { Link } from 'react-router-dom';
import { User, ShieldAlert, LogIn, UserPlus, Building2, LogOut, LayoutDashboard } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './Landing.css';

const Landing = () => {
  const { user, logout } = useAuth();

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
        <div className="badge">Tamil Nadu — AI-Powered Governance Security System</div>
        <h1>Governance Intelligence & Prioritization System</h1>
        <p>Secure AI-driven grievance classification, priority scoring, and decision intelligence for municipal governance.</p>
        <div className="hero-actions">
          <Link to="/citizen-services" className="btn-main">
            <User size={20} /> Citizen Portal
          </Link>
          <Link to="/government-portal" className="btn-main btn-secondary">
            <ShieldAlert size={20} /> Government Login
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
          <p>District-level command center with AI-driven insights, department analytics, and governance oversight.</p>
          <div className="role-actions">
            {user?.role === 'Executive' ? (
              <Link to="/executive" className="btn-role"><LayoutDashboard size={16} /> My Dashboard</Link>
            ) : (
              <Link to="/login" className="btn-role"><LogIn size={16} /> Login</Link>
            )}
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="footer-brand">GIIPS — Governance Incident Intelligence & Prioritization System</div>
        <div className="footer-links">
          <Link to="/methodology">Methodology</Link>
          <Link to="/citizen-services">Citizen Services</Link>
        </div>
        <div className="footer-copy">Tamil Nadu Municipal Governance Platform — Authorized Access Only</div>
      </footer>
    </div>
  );
};

export default Landing;