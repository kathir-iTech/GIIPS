import type React from 'react';
import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  LayoutDashboard,
  FileText,
  BarChart3,
  GitBranch,
  Map,
  BookOpen,
  LogIn,
  LogOut,
  User,
  ShieldAlert,
  Building2,
  Gauge,
  User as UserIcon,
  Settings,
  Users,
  Database,
  Menu,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './Sidebar.css';

const OFFICER_NAV = [
  { path: '/officer', key: 'nav.dashboard', icon: LayoutDashboard },
  { path: '/incident-feed', key: 'nav.incidents', icon: FileText },
  { path: '/clusters', key: 'nav.clusters', icon: GitBranch },
  { path: '/spatial', key: 'nav.spatial', icon: Map },
  { path: '/analysis', key: 'nav.analytics', icon: BarChart3 },
  { path: '/methodology', key: 'nav.methodology', icon: BookOpen },
];

const EXECUTIVE_NAV = [
  { path: '/executive', key: 'nav.executiveDashboard', icon: LayoutDashboard },
  { path: '/incident-feed', key: 'nav.incidents', icon: FileText },
  { path: '/clusters', key: 'nav.clusters', icon: GitBranch },
  { path: '/spatial', key: 'nav.spatial', icon: Map },
  { path: '/analysis', key: 'nav.analytics', icon: BarChart3 },
  { path: '/methodology', key: 'nav.methodology', icon: BookOpen },
];

const EXECUTIVE_ADMIN = [
  { path: '/admin/officers', key: 'nav.officerManagement', icon: Users },
  { path: '/admin/departments', key: 'nav.departmentManagement', icon: Building2 },
  { path: '/admin/system-health', key: 'nav.systemHealth', icon: Database },
  { path: '/admin/audit-logs', key: 'nav.auditLogs', icon: FileText },
];

const CITIZEN_NAV = [
  { path: '/citizen', key: 'nav.submitComplaint', icon: FileText },
  { path: '/my-complaints', key: 'nav.myComplaints', icon: UserIcon },
  { path: '/profile', key: 'nav.profile', icon: User },
];

const ROLE_KEYS: Record<string, string> = {
  Citizen: 'nav.roleCitizen',
  Officer: 'nav.roleOfficer',
  Executive: 'nav.roleExecutive',
};

const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems =
    user?.role === 'Executive'
      ? [...EXECUTIVE_NAV, { path: '/admin-divider' as const, key: 'nav.administration', icon: Settings }, ...EXECUTIVE_ADMIN]
      : user?.role === 'Officer'
        ? OFFICER_NAV
        : user?.role === 'Citizen'
          ? CITIZEN_NAV
          : [];

  const roleLabel = (role?: string) => t(ROLE_KEYS[role || ''] || role || '');

  return (
    <>
      <button className="hamburger-btn" onClick={() => setMobileOpen(!mobileOpen)} aria-label={t('nav.toggleMenu')}>
        {mobileOpen ? <X size={24} /> : <Menu size={24} />}
      </button>
      <div className={`sidebar-overlay ${mobileOpen ? 'open' : ''}`} onClick={() => setMobileOpen(false)} />
      <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon">
              <svg viewBox="0 0 40 40" fill="none">
                <rect width="40" height="40" rx="8" fill="#1e293b" />
                <path d="M20 8L32 16V32H8V16L20 8Z" stroke="white" strokeWidth="2" />
                <circle cx="20" cy="22" r="4" fill="white" />
              </svg>
            </div>
            <div className="logo-text">
              <span className="logo-title">{t('app.title')}</span>
              <span className="logo-subtitle">{t('app.subtitle')}</span>
            </div>
          </div>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(({ path, key, icon: Icon }) => {
            if (path === '/admin-divider') {
              return <div key={path} className="nav-divider">{t('nav.administration')}</div>;
            }
            return (
              <NavLink key={path} to={path} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={() => setMobileOpen(false)}>
                <Icon size={20} /> <span>{t(key)}</span>
              </NavLink>
            );
          })}
        </nav>
        {user ? (
          <button onClick={() => { logout(); setMobileOpen(false); }} className="nav-item logout-btn">
            <LogOut size={20} /> <span>{t('nav.logout')} ({roleLabel(user.role)})</span>
          </button>
        ) : (
          <NavLink to="/login" className="nav-item" onClick={() => setMobileOpen(false)}>
            <LogIn size={20} /> <span>{t('nav.login')}</span>
          </NavLink>
        )}
        <div className="sidebar-footer">
          <div className="version-badge"><span>{t('app.version')}</span></div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
