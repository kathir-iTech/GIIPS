import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import { User, Mail, Phone, MapPin, Shield, Edit3, Save, X } from 'lucide-react';
import './CitizenProfile.css';

const ROLE_KEYS: Record<string, string> = {
  Citizen: 'nav.roleCitizen',
  Officer: 'nav.roleOfficer',
  Executive: 'nav.roleExecutive',
};

const CitizenProfile = () => {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', district: '', ward: '' });
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api.getMe()
      .then(res => {
        setProfile(res);
        setForm({
          full_name: res.full_name || '',
          email: res.email || '',
          phone: res.phone || '',
          district: res.district || '',
          ward: res.ward || '',
        });
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const updated = await api.updateProfile(form);
      setProfile(updated);
      setMessage(t('profile.updateSuccess'));
      setEditing(false);
    } catch (err: any) {
      setMessage(err.message || t('profile.updateFailed'));
    } finally {
      setSaving(false);
    }
  };

  const roleLabel = (role?: string) => t(ROLE_KEYS[role || ''] || role || '');

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>{t('profile.loading')}</span></div>;
  if (error) return <div className="page-error">{t('common.error')}: {error}</div>;

  return (
    <div className="citizen-profile-page">
      <Header title={t('profile.headerTitle')} subtitle={t('profile.headerSubtitle')} />
      <div className="page-content">
        <div className="profile-card glass-card">
          <div className="profile-header">
            <div className="avatar">{profile?.full_name?.charAt(0)?.toUpperCase() || 'U'}</div>
            <div className="profile-title">
              <h2>{profile?.full_name || t('profile.defaultName')}</h2>
              <span className="role-badge">{roleLabel(profile?.role)}</span>
            </div>
            {!editing && (
              <button className="edit-btn" onClick={() => setEditing(true)}><Edit3 size={18} /> {t('profile.editButton')}</button>
            )}
          </div>

          {message && <div className="message-banner success">{message}</div>}

          <div className="profile-fields">
            <div className="field">
              <label><User size={16} /> {t('profile.fieldFullName')}</label>
              {editing ? (
                <input value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} />
              ) : (
                <span>{profile?.full_name || '—'}</span>
              )}
            </div>
            <div className="field">
              <label><Mail size={16} /> {t('profile.fieldEmail')}</label>
              {editing ? (
                <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
              ) : (
                <span>{profile?.email || '—'}</span>
              )}
            </div>
            <div className="field">
              <label><Phone size={16} /> {t('profile.fieldPhone')}</label>
              {editing ? (
                <input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} />
              ) : (
                <span>{profile?.phone || '—'}</span>
              )}
            </div>
            <div className="field">
              <label><MapPin size={16} /> {t('profile.fieldDistrict')}</label>
              {editing ? (
                <input value={form.district} onChange={e => setForm({ ...form, district: e.target.value })} />
              ) : (
                <span>{profile?.district || '—'}</span>
              )}
            </div>
            <div className="field">
              <label><Shield size={16} /> {t('profile.fieldWard')}</label>
              {editing ? (
                <input value={form.ward} onChange={e => setForm({ ...form, ward: e.target.value })} />
              ) : (
                <span>{profile?.ward || '—'}</span>
              )}
            </div>
          </div>

          {editing && (
            <div className="edit-actions">
              <button className="save-btn" onClick={handleSave} disabled={saving}><Save size={18} /> {saving ? t('profile.saving') : t('profile.saveChanges')}</button>
              <button className="cancel-btn" onClick={() => setEditing(false)} disabled={saving}><X size={18} /> {t('profile.cancel')}</button>
            </div>
          )}
        </div>

        <div className="info-card glass-card">
          <h3>{t('profile.aboutTitle')}</h3>
          <p>{t('profile.aboutBody', { role: roleLabel('Citizen') })}</p>
        </div>
      </div>
    </div>
  );
};

export default CitizenProfile;
