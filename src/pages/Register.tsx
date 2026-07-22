import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { UserPlus, Mail, Lock, User, Phone, AlertCircle, ArrowLeft } from 'lucide-react';
import './Auth.css';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^\d{10}$/;

const Register = () => {
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    phone: '',
    district: '',
    ward: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const { register, isLoading } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (!formData.email.trim()) {
      errs.email = t('citizenPortal.emailRequired');
    } else if (!EMAIL_RE.test(formData.email.trim())) {
      errs.email = t('citizenPortal.emailInvalid');
    } else if (formData.email.endsWith('@gov.in')) {
      errs.email = t('register.govAccountError');
    }
    if (!formData.password) {
      errs.password = t('citizenPortal.passwordRequired');
    } else if (formData.password.length < 8) {
      errs.password = t('citizenPortal.passwordMinLength');
    }
    if (formData.phone.trim() && !PHONE_RE.test(formData.phone.trim())) {
      errs.phone = t('citizenPortal.phoneInvalid');
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    try {
      await register(formData);
      navigate('/login');
    } catch (err: any) {
      setErrors({ api: err.message });
    }
  };

  const clearErr = (field: string) => { if (errors[field]) setErrors(prev => { const n = { ...prev }; delete n[field]; return n; }); };

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

        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          {errors.api && <div className="error-message"><AlertCircle size={16} /> {errors.api}</div>}

          <div className="form-group">
            <label htmlFor="full_name">{t('register.fullNameLabel')}</label>
            <div className="input-wrapper">
              <User size={18} className="input-icon" />
              <input
                id="full_name"
                type="text"
                placeholder={t('register.fullNamePlaceholder')}
                value={formData.full_name}
                onChange={e => { setFormData({ ...formData, full_name: e.target.value }); clearErr('full_name'); }}
                className={errors.full_name ? 'input-error' : ''}
                disabled={isLoading}
              />
            </div>
            {errors.full_name && <p className="field-error">{errors.full_name}</p>}
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
                onChange={e => { setFormData({ ...formData, email: e.target.value }); clearErr('email'); }}
                className={errors.email ? 'input-error' : ''}
                disabled={isLoading}
              />
            </div>
            {errors.email && <p className="field-error">{errors.email}</p>}
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
                onChange={e => { setFormData({ ...formData, password: e.target.value }); clearErr('password'); }}
                className={errors.password ? 'input-error' : ''}
                disabled={isLoading}
              />
            </div>
            {errors.password && <p className="field-error">{errors.password}</p>}
          </div>

          <div className="form-group">
            <label htmlFor="phone">{t('register.phoneLabel')}</label>
            <div className="input-wrapper">
              <Phone size={18} className="input-icon" />
              <input
                id="phone"
                type="tel"
                placeholder="9876543210"
                maxLength={10}
                value={formData.phone}
                onChange={e => { setFormData({ ...formData, phone: e.target.value.replace(/\D/g, '').slice(0, 10) }); clearErr('phone'); }}
                className={errors.phone ? 'input-error' : ''}
                disabled={isLoading}
              />
            </div>
            {errors.phone && <p className="field-error">{errors.phone}</p>}
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
