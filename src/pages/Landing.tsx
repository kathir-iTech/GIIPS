import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Trans } from 'react-i18next';
import { User, ShieldAlert, LogOut, LayoutDashboard, ArrowRight, AlertTriangle, Cpu, BarChart3, Search, Eye, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './Landing.css';

const BANNER_DISMISSED_KEY = 'giips_onboarding_dismissed';

const Landing = () => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
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
        <div className="brand">{t('landing.brand')}</div>
        {user && (
          <div className="nav-user">
            <Link to={dashboardPath!} className="nav-dashboard-btn">
              <LayoutDashboard size={16} /> {t('landing.navDashboard')}
            </Link>
            <button onClick={logout} className="nav-logout-btn">
              <LogOut size={16} /> {t('landing.navSignOut')}
            </button>
          </div>
        )}
      </nav>

      {!bannerDismissed && (
        <div className="onboarding-banner">
          <p>{t('landing.onboardingBanner')}</p>
          <button className="banner-close" onClick={dismissBanner} title={t('landing.dismissTitle')}><X size={16} /></button>
        </div>
      )}

      {/* ── Problem ── */}
      <section className="crystal-section problem-section">
        <div className="section-badge"><AlertTriangle size={14} /> {t('landing.problemBadge')}</div>
        <h2>{t('landing.problemTitle')}</h2>
        <p>{t('landing.problemBody')}</p>
      </section>

      {/* ── Solution ── */}
      <section className="crystal-section solution-section">
        <div className="section-badge"><Cpu size={14} /> {t('landing.solutionBadge')}</div>
        <h2>{t('landing.solutionTitle')}</h2>
        <p>{t('landing.solutionBody')}</p>
      </section>

      {/* ── Impact ── */}
      <section className="crystal-section impact-section">
        <div className="section-badge"><BarChart3 size={14} /> {t('landing.impactBadge')}</div>
        <h2>{t('landing.impactTitle')}</h2>
        <p>
          <Trans i18nKey="landing.impactBody">
            In a benchmark against 10,000 synthetic complaints, GIIPS collapsed them into 160 actionable incident
            clusters — reducing officer triage volume by 98.4%. Estimated time saved: <strong>~1,666 officer-hours</strong>.
          </Trans>
        </p>
        <p className="data-caveat">{t('landing.impactCaveat')}</p>
      </section>

      <section className="crystal-gateways">
        <Link to="/citizen-services" className="gateway-card">
          <div className="gateway-glow"></div>
          <div className="gateway-icon citizen-icon"><User size={36} /></div>
          <h2>{t('landing.citizenCardTitle')}</h2>
          <p>{t('landing.citizenCardBody')}</p>
          <span className="gateway-cta">{t('landing.citizenCardCta')} <ArrowRight size={16} /></span>
        </Link>

        <Link to="/government-portal" className="gateway-card">
          <div className="gateway-glow"></div>
          <div className="gateway-icon gov-icon"><ShieldAlert size={36} /></div>
          <h2>{t('landing.govCardTitle')}</h2>
          <p>{t('landing.govCardBody')}</p>
          <span className="gateway-cta">{t('landing.govCardCta')} <ArrowRight size={16} /></span>
        </Link>
      </section>

      <section className="crystal-section public-tools-section">
        <div className="section-badge"><Search size={14} /> {t('landing.toolsBadge')}</div>
        <h2>{t('landing.toolsTitle')}</h2>
        <p>{t('landing.toolsBody')}</p>
        <div className="public-tool-links">
          <Link to="/track" className="tool-link">
            <Search size={20} />
            <div>
              <strong>{t('landing.trackTitle')}</strong>
              <span>{t('landing.trackDesc')}</span>
            </div>
            <ArrowRight size={16} className="tool-arrow" />
          </Link>
          <Link to="/transparency" className="tool-link">
            <Eye size={20} />
            <div>
              <strong>{t('landing.transparencyTitle')}</strong>
              <span>{t('landing.transparencyDesc')}</span>
            </div>
            <ArrowRight size={16} className="tool-arrow" />
          </Link>
        </div>
      </section>

      <footer className="crystal-footer">
        <div className="footer-brand">{t('landing.footerBrand')}</div>
        <div className="footer-copy">{t('landing.footerCopy')}</div>
      </footer>
    </div>
  );
};

export default Landing;
