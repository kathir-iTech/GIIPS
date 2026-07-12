import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { LogIn, Mail, Lock, AlertCircle, ArrowLeft } from 'lucide-react';
import './Auth.css';

const Login = () => {
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const { login, isLoading } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login(formData.email, formData.password);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-bg">
        <div className="auth-orbe orbe-a"></div>
        <div className="auth-orbe orbe-b"></div>
      </div>
      <div className="auth-card glass-card">
        <button className="auth-back" onClick={() => navigate('/')}><ArrowLeft size={16} /> {t('login.backButton')}</button>
        <div className="auth-header">
          <LogIn size={32} className="auth-icon" />
          <h2>{t('login.title')}</h2>
          <p>{t('login.subtitle')}</p>
        </div>
        
        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="error-message"><AlertCircle size={16} /> {error}</div>}
          
          <div className="form-group">
            <label htmlFor="email">{t('login.emailLabel')}</label>
            <div className="input-wrapper">
              <Mail size={18} className="input-icon" />
              <input
                id="email"
                type="email"
                placeholder={t('login.emailPlaceholder')}
                value={formData.email}
                onChange={e => setFormData({ ...formData, email: e.target.value })}
                required
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="password">{t('login.passwordLabel')}</label>
            <div className="input-wrapper">
              <Lock size={18} className="input-icon" />
              <input
                id="password"
                type="password"
                placeholder={t('login.passwordPlaceholder')}
                value={formData.password}
                onChange={e => setFormData({ ...formData, password: e.target.value })}
                required
                disabled={isLoading}
              />
            </div>
          </div>

          <button type="submit" className="auth-button" disabled={isLoading}>
            {isLoading ? t('login.submittingButton') : t('login.submitButton')}
          </button>
        </form>

        <div className="auth-footer">
          <p>{t('login.footerText')} <Link to="/register">{t('login.footerLink')}</Link></p>
        </div>
      </div>
    </div>
  );
};

export default Login;
