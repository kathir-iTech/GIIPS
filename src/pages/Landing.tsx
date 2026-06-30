import { Link } from 'react-router-dom';
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
          <Link to="/roles" className="nav-link">Portal</Link>
          <Link to="/roles" className="cta-button">Initialize Demo</Link>
        </div>
      </nav>
      
      <header className="hero-os">
        <div className="badge">Government Intelligence Powered by AI</div>
        <h1>Governance Intelligence & Prioritization System</h1>
        <p>A unified command layer for municipal infrastructure management.</p>
        <Link to="/roles" className="btn-main">Initialize AI System</Link>
      </header>

      <section className="dashboard-preview">
        <div className="glass-card preview-box">
          <div className="preview-header">
            <div className="dot red"></div><div className="dot yellow"></div><div className="dot green"></div>
          </div>
          <div className="preview-content">
            {/* Visual placeholder representing the command center */}
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
