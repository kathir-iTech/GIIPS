import type React from 'react';
import { NavLink } from 'react-router-dom';
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
  LineChart,
  Building2,
  Gauge,
  FileText as FileTextIcon,
  User as UserIcon
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './Sidebar.css';

const OFFICER_NAV = [
  { path: '/officer', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/incident-feed', label: 'Incidents', icon: FileText },
  { path: '/clusters', label: 'Clusters', icon: GitBranch },
  { path: '/spatial', label: 'Spatial Intelligence', icon: Map },
  { path: '/analysis', label: 'Analytics', icon: BarChart3 },
  { path: '/methodology', label: 'Methodology', icon: BookOpen },
];

const EXECUTIVE_NAV = [
  { path: '/executive', label: 'Executive Dashboard', icon: LayoutDashboard },
  { path: '/incident-feed', label: 'Incidents', icon: FileText },
  { path: '/clusters', label: 'Clusters', icon: GitBranch },
  { path: '/spatial', label: 'Spatial Intelligence', icon: Map },
  { path: '/analysis', label: 'Analytics', icon: BarChart3 },
  { path: '/methodology', label: 'Methodology', icon: BookOpen },
];

const CITIZEN_NAV = [
  { path: '/citizen', label: 'Submit Complaint', icon: FileTextIcon },
  { path: '/my-complaints', label: 'My Complaints', icon: UserIcon },
  { path: '/profile', label: 'Profile', icon: User },
];

const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();

  const navItems =
    user?.role === 'Executive'
      ? EXECUTIVE_NAV
      : user?.role === 'Officer'
        ? OFFICER_NAV
        : user?.role === 'Citizen'
          ? CITIZEN_NAV
          : [];

  return (
    <aside className="sidebar">
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
            <span className="logo-title">GIIPS</span>
            <span className="logo-subtitle">Governance Intelligence</span>
          </div>
        </div>
      </div>
      <nav className="sidebar-nav">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink key={path} to={path} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Icon size={20} /> <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      {user ? (
        <button onClick={logout} className="nav-item logout-btn">
          <LogOut size={20} /> <span>Logout ({user.role})</span>
        </button>
      ) : (
        <NavLink to="/login" className="nav-item">
          <LogIn size={20} /> <span>Login</span>
        </NavLink>
      )}
      <div className="sidebar-footer">
        <div className="version-badge"><span>Platform v2.1</span></div>
        <div className="footer-text">
          <p>Municipal Corporation</p>
          <p>Decision Support System</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
