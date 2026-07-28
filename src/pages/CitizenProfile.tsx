import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import { User, Mail, Phone, MapPin, Shield, Edit3, Save, X, Bell, BellOff, Building2, BarChart3, Activity } from 'lucide-react';
import { getCouncillorByWard } from '../data/councillors';
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
  const [notifLoading, setNotifLoading] = useState(false);
  const [userAvailability, setUserAvailability] = useState('available');
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState('');
  const [impactScore, setImpactScore] = useState(0);
  const [impactLabel, setImpactLabel] = useState('Low');
  const [complaints, setComplaints] = useState<any[]>([]);

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
        if (res.skills) {
          try { setSkills(JSON.parse(res.skills)); } catch { setSkills([]); }
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
    api.getMyComplaints().then(res => {
      const items = Array.isArray(res.complaints) ? res.complaints : [];
      setComplaints(items);
      const total = items.length;
      const resolved = items.filter((c: any) => c.incident?.status === 'closed' || c.incident?.status === 'resolved').length;
      const verified = items.filter((c: any) => c.citizen_rating != null).length;
      let score = total > 0 ? (resolved / total) * 100 : 0;
      score += Math.min(verified * 5, 20);
      score = Math.min(Math.round(score), 100);
      setImpactScore(score);
      setImpactLabel(score >= 70 ? t('citizenProfile.impactHigh') : score >= 40 ? t('citizenProfile.impactMedium') : t('citizenProfile.impactLow'));
    }).catch(() => {});
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

  const handleToggleNotifications = async () => {
    setNotifLoading(true);
    try {
      const current = profile?.notify_status_updates ?? true;
      const res = await api.updateNotificationPrefs(!current);
      setProfile((p: any) => ({ ...p, notify_status_updates: res.notify_status_updates }));
    } catch (err: any) {
      setMessage(err.message || t('citizenProfile.notifUpdateError'));
    } finally {
      setNotifLoading(false);
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
            <div className="field">
              <label><BarChart3 size={16} /> {t('citizenProfile.impactScore')}</label>
              <span>{t('citizenProfile.impactScoreValue', { score: impactScore, label: impactLabel })}</span>
            </div>
          </div>

          {editing && (
            <div className="edit-actions">
              <button className="save-btn" onClick={handleSave} disabled={saving}><Save size={18} /> {saving ? t('profile.saving') : t('profile.saveChanges')}</button>
              <button className="cancel-btn" onClick={() => setEditing(false)} disabled={saving}><X size={18} /> {t('profile.cancel')}</button>
            </div>
          )}
        </div>

        {(() => {
          const ward = profile?.ward || user?.ward || '';
          const councillor = ward ? getCouncillorByWard(ward) : undefined;
          return (
            <div className="profile-card glass-card">
              <div className="profile-header">
                <Building2 size={20} />
                <div className="profile-title">
                  <h2>{t('profile.councillorSection')}</h2>
                  <span className="role-badge">{t('profile.councillorRole')}</span>
                </div>
              </div>
              {councillor ? (
                <div className="councillor-details">
                  <div className="councillor-field">
                    <span className="councillor-label">{t('profile.fieldFullName')}</span>
                    <span className="councillor-value">{councillor.name}</span>
                  </div>
                  <div className="councillor-field">
                    <span className="councillor-label">{t('profile.councillorPhone')}</span>
                    <span className="councillor-value">
                      <a href={`tel:${councillor.phone}`} className="councillor-phone-link">{councillor.phone}</a>
                    </span>
                  </div>
                  <div className="councillor-field">
                    <span className="councillor-label">{t('profile.fieldWard')}</span>
                    <span className="councillor-value">{t('citizenProfile.wardPrefix', { ward: councillor.ward })}</span>
                  </div>
                </div>
              ) : (
                <p className="councillor-empty">{t('profile.councillorNotAssigned')}</p>
              )}
            </div>
          );
        })()}

        <div className="profile-card glass-card">
          <div className="profile-header">
            <Bell size={20} />
            <div className="profile-title">
              <h2>{t('citizenProfile.notificationsSection')}</h2>
              <span className="role-badge">{t('citizenProfile.notifBadge')}</span>
            </div>
          </div>
          <div className="notif-toggle-row">
            <div className="notif-toggle-info">
              <span className="notif-toggle-label">{t('citizenProfile.notifToggleLabel')}</span>
              <span className="notif-toggle-desc">{t('citizenProfile.notifToggleDesc')}</span>
            </div>
            <button
              className={`notif-toggle-btn ${profile?.notify_status_updates !== false ? 'active' : ''}`}
              onClick={handleToggleNotifications}
              disabled={notifLoading}
            >
              {notifLoading ? (
                <div className="spinner-sm" />
              ) : profile?.notify_status_updates !== false ? (
                <><Bell size={16} /> {t('citizenProfile.notifOn')}</>
              ) : (
                <><BellOff size={16} /> {t('citizenProfile.notifOff')}</>
              )}
            </button>
          </div>
        </div>

        {complaints.length > 0 && (() => {
          const catCounts: Record<string, number> = {};
          const wardCounts: Record<string, number> = {};
          let totalDaysSaved = 0;
          for (const c of complaints) {
            const cat = c.predicted_category || 'Uncategorized';
            catCounts[cat] = (catCounts[cat] || 0) + 1;
            const w = c.ward || 'Unknown';
            wardCounts[w] = (wardCounts[w] || 0) + 1;
            if (c.incident?.days_open != null && ['closed', 'resolved'].includes(c.incident.status || '')) {
              totalDaysSaved += c.incident.days_open;
            }
          }
          const maxCatCount = Math.max(...Object.values(catCounts), 1);
          const mostActiveWard = Object.entries(wardCounts).sort((a, b) => b[1] - a[1])[0];
          const CAT_COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#16a34a', '#dc2626', '#06b6d4', '#ea580c'];
          const catEntries = Object.entries(catCounts).sort((a, b) => b[1] - a[1]);
          return (
            <div className="profile-card glass-card">
              <div className="profile-header">
                <Activity size={20} />
                <div className="profile-title">
                  <h2>{t('citizenAnalytics.title')}</h2>
                </div>
              </div>
              <div className="analytics-section">
                <div className="analytics-bars">
                  <h4>{t('citizenAnalytics.complaintCountByCategory')}</h4>
                  {catEntries.map(([cat, count], i) => (
                    <div key={cat} className="analytics-bar-row">
                      <span className="analytics-bar-label">{cat}</span>
                      <div className="analytics-bar-track">
                        <div className="analytics-bar-fill" style={{ width: `${(count / maxCatCount) * 100}%`, background: CAT_COLORS[i % CAT_COLORS.length] }} />
                      </div>
                      <span className="analytics-bar-count">{count}</span>
                    </div>
                  ))}
                </div>
                <div className="analytics-meta">
                  {mostActiveWard && (
                    <div className="analytics-meta-item">
                      <span className="analytics-meta-label">{t('citizenAnalytics.mostActiveWard')}</span>
                      <span className="analytics-meta-value">{mostActiveWard[0]} ({mostActiveWard[1]})</span>
                    </div>
                  )}
                  <div className="analytics-meta-item">
                    <span className="analytics-meta-label">{t('citizenAnalytics.totalDaysSaved')}</span>
                    <span className="analytics-meta-value">{totalDaysSaved}{t('citizenAnalytics.daysUnit')}</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}

        {user?.role === 'Officer' && (
          <div className="profile-card glass-card">
            <div className="profile-header">
              <div className="profile-title">
                <h2>{t('citizenProfile.availability')}</h2>
              </div>
            </div>
            <div className="avail-toggle-row">
              <button className={`avail-btn ${userAvailability === 'available' ? 'active-avail' : ''}`}
                onClick={() => api.updateAvailability('available').then(() => setUserAvailability('available'))}>
                {t('citizenProfile.available')}
              </button>
              <button className={`avail-btn ${userAvailability === 'on_leave' ? 'active-leave' : ''}`}
                onClick={() => api.updateAvailability('on_leave').then(() => setUserAvailability('on_leave'))}>
                {t('citizenProfile.onLeave')}
              </button>
            </div>
          </div>
        )}
        {user?.role === 'Officer' && (
          <div className="profile-card glass-card">
            <div className="profile-header">
              <div className="profile-title">
                <h2>{t('citizenProfile.skillsSection')}</h2>
              </div>
            </div>
            <div className="skills-section">
              <div className="skills-list">
                {skills.map((s, i) => (
                  <span key={i} className="skill-badge">{s} <span className="skill-remove" onClick={() => setSkills(prev => { const next = prev.filter((_, j) => j !== i); api.updateSkills(next); return next; })}>×</span></span>
                ))}
              </div>
              <div className="skill-input-row">
                <input value={skillInput} onChange={e => setSkillInput(e.target.value)} placeholder={t('citizenProfile.addSkillPlaceholder')} className="skill-input"
                  onKeyDown={e => { if (e.key === 'Enter' && skillInput.trim() && !skills.includes(skillInput.trim())) { const newSkills = [...skills, skillInput.trim()]; setSkills(newSkills); setSkillInput(''); api.updateSkills(newSkills); }}}
                />
              </div>
            </div>
          </div>
        )}

        <div className="info-card glass-card">
          <h3>{t('profile.aboutTitle')}</h3>
          <p>{t('profile.aboutBody', { role: roleLabel('Citizen') })}</p>
        </div>
      </div>
    </div>
  );
};

export default CitizenProfile;
