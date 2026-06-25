import type React from 'react';
import './Header.css';

interface HeaderProps { title: string; subtitle?: string; }

const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  const currentDate = new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  const currentTime = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  return (
    <header className="header">
      <div className="header-left">
        <h1 className="page-title">{title}</h1>
        {subtitle && <span className="page-subtitle">{subtitle}</span>}
      </div>
      <div className="header-right">
        <div className="header-datetime">
          <span className="current-date">{currentDate}</span>
          <span className="current-time">{currentTime}</span>
        </div>
        <div className="header-badge">
          <span className="badge-label">System Status</span>
          <span className="badge-value online">Operational</span>
        </div>
      </div>
    </header>
  );
};

export default Header;
