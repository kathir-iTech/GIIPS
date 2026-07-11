import { Link } from 'react-router-dom';
import { User, ShieldAlert, LogOut, LayoutDashboard, ArrowRight } from 'lucide-react';
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
      <div className="crystal-bg">
        <div className="crystal-orbe orbe-1"></div>
        <div className="crystal-orbe orbe-2"></div>
        <div className="crystal-orbe orbe-3"></div>
        <div className="crystal-orbe orbe-4"></div>
      </div>

      <nav className="crystal-nav">
        <div className="brand">GIIPS <span>OS</span></div>
        {user && (
          <div className="nav-user">
            <Link to={dashboardPath!} className="nav-dashboard-btn">
              <LayoutDashboard size={16} /> Dashboard
            </Link>
            <button onClick={logout} className="nav-logout-btn">
              <LogOut size={16} /> Sign Out
            </button>
          </div>
        )}
      </nav>

      <header className="crystal-hero">
        <div className="hero-badge">Tamil Nadu — AI-Powered Governance Security System</div>
        <h1>Governance Intelligence & Prioritization System</h1>
        <p>Secure AI-driven grievance classification, priority scoring, and decision intelligence for municipal governance.</p>
      </header>

      <section className="crystal-gateways">
        <Link to="/citizen-services" className="gateway-card">
          <div className="gateway-glow"></div>
          <div className="gateway-icon citizen-icon"><User size={36} /></div>
          <h2>Citizen Portal</h2>
          <p>Submit grievances, track AI-classified complaints, and monitor resolution progress in real time.</p>
          <span className="gateway-cta">Enter Portal <ArrowRight size={16} /></span>
        </Link>

        <Link to="/government-portal" className="gateway-card">
          <div className="gateway-glow"></div>
          <div className="gateway-icon gov-icon"><ShieldAlert size={36} /></div>
          <h2>Government Login</h2>
          <p>Authorized personnel access — incident command, department analytics, and AI governance oversight.</p>
          <span className="gateway-cta">Secure Access <ArrowRight size={16} /></span>
        </Link>
      </section>

      <footer className="crystal-footer">
        <div className="footer-brand">GIIPS — Governance Incident Intelligence & Prioritization System</div>
        <div className="footer-copy">Tamil Nadu Municipal Governance Platform — Authorized Access Only</div>
      </footer>
    </div>
  );
};

export default Landing;
