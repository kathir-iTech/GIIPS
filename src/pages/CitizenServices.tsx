import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { UserPlus, LogIn, User, Search } from 'lucide-react';
import './Auth.css';

const CitizenServices = () => {
  const { t } = useTranslation();
  return (
    <div className="auth-page">
      <div className="auth-card glass-card">
        <div className="auth-header">
          <User size={32} className="auth-icon" />
          <h2>{t('citizenServices.title')}</h2>
          <p>{t('citizenServices.subtitle')}</p>
        </div>
        
        <div className="auth-form">
          <Link to="/register" className="auth-button">
            <UserPlus size={18} className="input-icon" />
            {t('citizenServices.registerButton')}
          </Link>
          <Link to="/login" className="auth-button secondary">
            <LogIn size={18} className="input-icon" />
            {t('citizenServices.loginButton')}
          </Link>
        </div>

        <div className="auth-footer-links">
          <Link to="/track" className="auth-footer-link">
            <Search size={14} />
            {t('citizenServices.trackExisting')}
          </Link>
          <span className="auth-footer-sep">·</span>
          <Link to="/login" className="auth-footer-link">
            <LogIn size={14} />
            {t('citizenServices.forgotId')}
          </Link>
        </div>
      </div>
    </div>
  );
};

export default CitizenServices;
