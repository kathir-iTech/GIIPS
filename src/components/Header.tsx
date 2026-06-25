import type React from 'react';
import { Bell, User } from 'lucide-react';
import './Header.css';

interface HeaderProps { title: string; subtitle?: string; }

const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  const currentDate = new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  return (
    <header className="header">
      <div className="header-left">
        <h1 className="page-title">{title}</h1>
        {subtitle && <span className="page-subtitle">{subtitle}</span>}
      </div>
      <div className="header-right">
        <span className="current-date">{currentDate}</span>
        <div className="header-actions">
          <button className="header-btn"><Bell size={20} /><span className="notification-badge">3</span></button>
          <button className="header-btn user-btn"><User size={20} /><span className="user-name">Municipal Commissioner</span></button>
        </div>
      </div>
    </header>
  );
};

export default Header;
