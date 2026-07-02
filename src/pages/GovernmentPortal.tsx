import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, LogIn } from 'lucide-react';
import './Auth.css';

const GovernmentPortal = () => {
  return (
    <div className="auth-page">
      <div className="auth-card glass-card">
        <div className="auth-header">
          <ShieldAlert size={32} className="auth-icon" />
          <h2>Government Portal</h2>
          <p>Officer and Executive login</p>
        </div>
        
        <div className="auth-form">
          <Link to="/login" className="auth-button">
            <LogIn size={18} className="input-icon" />
            Government Login
          </Link>
        </div>
      </div>
    </div>
  );
};

export default GovernmentPortal;