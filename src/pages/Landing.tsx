import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Trans } from 'react-i18next';
import { User, ShieldAlert, LogOut, LayoutDashboard, ArrowRight, AlertTriangle, Cpu, BarChart3, Search, Eye, X, Hash, Image } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import './Landing.css';

const CATEGORY_COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#16a34a', '#dc2626', '#06b6d4', '#ea580c'];
const BANNER_DISMISSED_KEY = 'giips_onboarding_dismissed';

const Landing = () => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const [bannerDismissed, setBannerDismissed] = React.useState(
    () => localStorage.getItem(BANNER_DISMISSED_KEY) === 'true'
  );
  const [installPrompt, setInstallPrompt] = useState<any>(null);
  const [catStats, setCatStats] = useState<{ category: string; count: number }[] | null>(null);
  const [complaintsHandled, setComplaintsHandled] = useState<number>(0);
  const [animatedCount, setAnimatedCount] = useState<number>(0);
  const counterRef = useRef<HTMLSpanElement>(null);
  const prevCountRef = useRef<number>(0);
  const animFrameRef = useRef<number>(0);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstallClick = () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    installPrompt.userChoice.then((result: { outcome: string }) => {
      if (result.outcome === 'accepted') setInstallPrompt(null);
    });
  };

  useEffect(() => {
    if (animatedCount !== complaintsHandled) {
      const start = animatedCount;
      const end = complaintsHandled;
      const duration = 800;
      const startTime = performance.now();
      const animate = (now: number) => {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        setAnimatedCount(Math.round(start + (end - start) * eased));
        if (progress < 1) animFrameRef.current = requestAnimationFrame(animate);
      };
      animFrameRef.current = requestAnimationFrame(animate);
    }
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [complaintsHandled]);

  useEffect(() => {
    const fetchStats = () => {
      api.getPublicStats()
        .then(d => {
          setCatStats(d.complaintsByCategory || []);
          const newCount = d.totalComplaintsThisMonth || 0;
          prevCountRef.current = complaintsHandled;
          setComplaintsHandled(newCount);
        })
        .catch(() => {});
    };
    fetchStats();
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, []);

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

      {installPrompt && (
        <div className="install-banner">
          <span>{t('landing.installPrompt')}</span>
          <button className="install-btn" onClick={handleInstallClick}>{t('landing.installButton')}</button>
          <button className="banner-close" onClick={() => setInstallPrompt(null)}><X size={16} /></button>
        </div>
      )}

      {complaintsHandled > 0 && (
        <section className="crystal-section counter-section">
          <div className="counter-badge">{t('landing.counterBadge')}</div>
          <div className="counter-value">
            <span className="counter-number" ref={counterRef}>{animatedCount.toLocaleString()}</span>
          </div>
          <p className="counter-label">{t('landing.counterLabel')}</p>
        </section>
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

      {catStats && catStats.length > 0 && (
        <section className="crystal-section mini-chart-section">
          <div className="section-badge"><BarChart3 size={14} /> {t('landing.chartBadge')}</div>
          <h2>{t('landing.chartTitle')}</h2>
          <div className="mini-chart">
            <div className="mini-chart-bars">
              {catStats.map((c, i) => {
                const maxCount = catStats[0].count;
                const pct = (c.count / maxCount) * 100;
                return (
                  <div key={c.category} className="mini-chart-row">
                    <span className="mini-chart-label">{c.category}</span>
                    <div className="mini-chart-track">
                      <div
                        className="mini-chart-fill"
                        style={{ width: `${pct}%`, background: CATEGORY_COLORS[i % CATEGORY_COLORS.length] }}
                      />
                    </div>
                    <span className="mini-chart-count">{c.count.toLocaleString()}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}

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
          <Link to="/resolved-gallery" className="tool-link">
            <Image size={20} />
            <div>
              <strong>{t('landing.resolvedGalleryTitle')}</strong>
              <span>{t('landing.resolvedGalleryDesc')}</span>
            </div>
            <ArrowRight size={16} className="tool-arrow" />
          </Link>
        </div>
      </section>

      <footer className="crystal-footer">
        <div className="footer-brand">{t('landing.footerBrand')}</div>
        <div className="footer-links">
          <Link to="/categories" className="footer-link">{t('landing.categoriesTitle')}</Link>
          <span className="footer-sep">·</span>
          <Link to="/transparency" className="footer-link">{t('landing.transparencyTitle')}</Link>
          <span className="footer-sep">·</span>
          <Link to="/methodology" className="footer-link">{t('methodology.header.title')}</Link>
        </div>
        <div className="footer-copy">{t('landing.footerCopy')}</div>
      </footer>
    </div>
  );
};

export default Landing;
