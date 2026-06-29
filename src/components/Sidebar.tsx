import type React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FileText, ChartBar as BarChart3, GitBranch, BookOpen, Map } from 'lucide-react';
import './Sidebar.css';

const navItems = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/incidents', label: 'Incident Feed', icon: FileText },
  { path: '/analysis', label: 'Complaint Analysis', icon: BarChart3 },
  { path: '/clusters', label: 'Cluster Explorer', icon: GitBranch },
  { path: '/spatial', label: 'Spatial Intelligence', icon: Map },
  { path: '/methodology', label: 'Methodology', icon: BookOpen },
];

const Sidebar: React.FC = () => (
  <aside className="sidebar">
    <div className="sidebar-header">
      <div className="logo">
        <div className="logo-icon">
          <svg viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#1e293b"/><path d="M20 8L32 16V32H8V16L20 8Z" stroke="white" strokeWidth="2"/><circle cx="20" cy="22" r="4" fill="white"/></svg>
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
    <div className="sidebar-footer">
      <div className="version-badge"><span>Platform v2.1</span></div>
      <div className="footer-text"><p>Municipal Corporation</p><p>Decision Support System</p></div>
    </div>
  </aside>
);

export default Sidebar;
