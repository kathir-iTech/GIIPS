import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { UserPlus, Mail, Lock, User, AlertCircle, ArrowLeft } from 'lucide-react';
import './Auth.css';

const Register = () => {
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    phone: '',
    district: '',
    ward: '',
  });
  const [error, setError] = useState('');
  const { register, isLoading } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (formData.email.endsWith('@gov.in')) {
      setError(t('register.govAccountError'));
      return;
    }
    try {
      await register(formData);
      navigate('/login');
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
        <button className="auth-back" onClick={() => navigate('/')}><ArrowLeft size={16} /> {t('register.backButton')}</button>
        <div className="auth-header">
          <UserPlus size={32} className="auth-icon" />
          <h2>{t('register.title')}</h2>
          <p>{t('register.subtitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="error-message"><AlertCircle size={16} /> {error}</div>}

          <div className="form-group">
            <label htmlFor="full_name">{t('register.fullNameLabel')}</label>
            <div className="input-wrapper">
              <User size={18} className="input-icon" />
              <input
                id="full_name"
                type="text"
                placeholder={t('register.fullNamePlaceholder')}
                value={formData.full_name}
                onChange={e => setFormData({ ...formData, full_name: e.target.value })}
                required
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="email">{t('register.emailLabel')}</label>
            <div className="input-wrapper">
              <Mail size={18} className="input-icon" />
              <input
                id="email"
                type="email"
                placeholder={t('register.emailPlaceholder')}
                value={formData.email}
                onChange={e => setFormData({ ...formData, email: e.target.value })}
                required
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="password">{t('register.passwordLabel')}</label>
            <div className="input-wrapper">
              <Lock size={18} className="input-icon" />
              <input
                id="password"
                type="password"
                placeholder={t('register.passwordPlaceholder')}
                value={formData.password}
                onChange={e => setFormData({ ...formData, password: e.target.value })}
                required
                disabled={isLoading}
              />
            </div>
          </div>

          <button type="submit" className="auth-button" disabled={isLoading}>
            {isLoading ? t('register.submittingButton') : t('register.submitButton')}
          </button>
        </form>

        <div className="auth-footer">
          <p>{t('register.footerText')} <Link to="/login">{t('register.footerLink')}</Link></p>
        </div>
      </div>
    </div>
  );
};

export default Register;
