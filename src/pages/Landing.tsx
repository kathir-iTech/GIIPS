import React from 'react';
import { Link } from 'react-router-dom';
import { User, ShieldAlert, LogOut, LayoutDashboard, ArrowRight, AlertTriangle, Cpu, BarChart3, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './Landing.css';

const BANNER_DISMISSED_KEY = 'giips_onboarding_dismissed';

const Landing = () => {
  const { user, logout } = useAuth();
  const [bannerDismissed, setBannerDismissed] = React.useState(
    () => localStorage.getItem(BANNER_DISMISSED_KEY) === 'true'
  );

  const dismissBanner = () => {
    setBannerDismissed(true);
    localStorage.setItem(BANNER_DISMISSED_KEY, 'true');
  };

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

      {!bannerDismissed && (
        <div className="onboarding-banner">
          <p>
            GIIPS is an AI-assisted triage layer designed to work alongside official Tamil Nadu grievance
            systems — it is a hackathon prototype demonstrating automated complaint clustering and
            prioritization, not a replacement for government portals.
          </p>
          <button className="banner-close" onClick={dismissBanner} title="Dismiss"><X size={16} /></button>
        </div>
      )}

      {/* ── Problem ── */}
      <section className="crystal-section problem-section">
        <div className="section-badge"><AlertTriangle size={14} /> The Problem</div>
        <h2>Municipal staff are overwhelmed by complaint volume</h2>
        <p>
          Citizens report the same issues repeatedly. Officers manually read and triage each one, with no way to
          automatically detect duplicates or prioritize urgent cases. Critical problems get buried, and response
          times suffer.
        </p>
      </section>

      {/* ── Solution ── */}
      <section className="crystal-section solution-section">
        <div className="section-badge"><Cpu size={14} /> The Solution</div>
        <h2>An AI triage layer for existing grievance workflows</h2>
        <p>
          GIIPS automatically classifies incoming complaints, merges duplicates into a single incident, and
          assigns a priority score — so officers review fewer, more actionable items. It is designed as a
          supplemental triage layer, not a replacement for official government portals.
        </p>
      </section>

      {/* ── Impact ── */}
      <section className="crystal-section impact-section">
        <div className="section-badge"><BarChart3 size={14} /> Measured Impact</div>
        <h2>Reducing incidents to review by 98%</h2>
        <p>
          In a benchmark against 10,000 synthetic complaints, GIIPS collapsed them into 160 actionable incident
          clusters — reducing officer triage volume by 98.4%. Estimated time saved: <strong>~1,666 officer-hours</strong>.
        </p>
        <p className="data-caveat">
          These figures are based on synthetic complaint data (not live grievance records) using an SBERT-based
          clustering model. Real-world free-text data with greater linguistic variety would likely yield a lower
          reduction rate, bounded below by an alternative TF-IDF estimate of ~50%. The metric is a validated
          upper bound, not a production guarantee.
        </p>
      </section>

      <section className="crystal-gateways">
        <Link to="/citizen-services" className="gateway-card">
          <div className="gateway-glow"></div>
          <div className="gateway-icon citizen-icon"><User size={36} /></div>
          <h2>Citizen Portal</h2>
          <p>Submit and track complaints. See how your issue is categorized and prioritized.</p>
          <span className="gateway-cta">Enter Portal <ArrowRight size={16} /></span>
        </Link>

        <Link to="/government-portal" className="gateway-card">
          <div className="gateway-glow"></div>
          <div className="gateway-icon gov-icon"><ShieldAlert size={36} /></div>
          <h2>Government Login</h2>
          <p>Review incidents, monitor department performance, and access AI-assisted insights.</p>
          <span className="gateway-cta">Secure Access <ArrowRight size={16} /></span>
        </Link>
      </section>

      <footer className="crystal-footer">
        <div className="footer-brand">GIIPS — AI triage layer prototype</div>
        <div className="footer-copy">Not affiliated with or endorsed by any government entity.</div>
      </footer>
    </div>
  );
};

export default Landing;
