import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, LogIn, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './Auth.css';

const GovernmentPortal = () => {
  const navigate = useNavigate();
  return (
    <div className="auth-page">
      <div className="auth-bg">
        <div className="auth-orbe orbe-a"></div>
        <div className="auth-orbe orbe-b"></div>
      </div>
      <div className="auth-card glass-card">
        <button className="auth-back" onClick={() => navigate('/')}><ArrowLeft size={16} /> Back</button>
        <div className="auth-header">
          <ShieldAlert size={32} className="auth-icon" />
          <h2>Government Login</h2>
          <p>Authorized personnel only — @gov.in accounts</p>
        </div>
        
        <div className="auth-form">
          <Link to="/login" className="auth-button">
            <LogIn size={18} />
            Sign In
          </Link>
          <p style={{ textAlign: 'center', color: '#64748b', fontSize: '13px', marginTop: '8px' }}>
            Government accounts are created by your Executive. Contact them if you need access.
          </p>
        </div>
      </div>
    </div>
  );
};

export default GovernmentPortal;
