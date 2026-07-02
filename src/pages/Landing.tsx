import { Link } from 'react-router-dom';
import { User, ShieldAlert, Play } from 'lucide-react';
import './Landing.css';

const Landing = () => {
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
        </div>
      </nav>
      
      <header className="hero-os">
        <div className="badge">Government Intelligence Powered by AI</div>
        <h1>Governance Intelligence & Prioritization System</h1>
        <p>A unified command layer for municipal infrastructure management.</p>
        <div className="hero-actions">
          <Link to="/citizen-services" className="btn-main">Access Services</Link>
          <Link to="/demo" className="btn-demo">
            <Play size={20} /> Start Demo
          </Link>
        </div>
      </header>

      <section className="dashboard-preview">
        <div className="glass-card preview-box">
          <div className="preview-header">
            <div className="dot red"></div><div className="dot yellow"></div><div className="dot green"></div>
          </div>
          <div className="preview-content">
            <div className="mock-grid">
              <div className="mock-card"></div><div className="mock-card"></div><div className="mock-card"></div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Landing;