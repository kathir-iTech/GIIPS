import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { LogIn, Mail, Lock, AlertCircle, ArrowLeft } from 'lucide-react';
import './Auth.css';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const Login = () => {
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState<{ email?: string; password?: string; api?: string }>({});
  const { login, isLoading } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const validate = (): boolean => {
    const errs: typeof errors = {};
    if (!formData.email.trim()) {
      errs.email = t('citizenPortal.emailRequired');
    } else if (!EMAIL_RE.test(formData.email.trim())) {
      errs.email = t('citizenPortal.emailInvalid');
    }
    if (!formData.password) {
      errs.password = t('citizenPortal.passwordRequired');
    } else if (formData.password.length < 8) {
      errs.password = t('citizenPortal.passwordMinLength');
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    try {
      await login(formData.email, formData.password);
    } catch (err: any) {
      setErrors({ api: err.message });
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
        
        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          {errors.api && <div className="error-message"><AlertCircle size={16} /> {errors.api}</div>}
          
          <div className="form-group">
            <label htmlFor="email">{t('login.emailLabel')}</label>
            <div className="input-wrapper">
              <Mail size={18} className="input-icon" />
              <input
                id="email"
                type="email"
                placeholder={t('login.emailPlaceholder')}
                value={formData.email}
                onChange={e => { setFormData({ ...formData, email: e.target.value }); if (errors.email) setErrors(prev => ({ ...prev, email: undefined })); }}
                className={errors.email ? 'input-error' : ''}
                disabled={isLoading}
              />
            </div>
            {errors.email && <p className="field-error">{errors.email}</p>}
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
                onChange={e => { setFormData({ ...formData, password: e.target.value }); if (errors.password) setErrors(prev => ({ ...prev, password: undefined })); }}
                className={errors.password ? 'input-error' : ''}
                disabled={isLoading}
              />
            </div>
            {errors.password && <p className="field-error">{errors.password}</p>}
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
