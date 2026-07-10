import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import { User, Mail, Phone, MapPin, Shield, Edit3, Save, X } from 'lucide-react';
import './CitizenProfile.css';

const CitizenProfile = () => {
  const { user, token } = useAuth();
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', district: '', ward: '' });
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    api.getMe(token)
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
  }, [token]);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const updated = await api.updateProfile(form, token!);
      localStorage.setItem('giips_user', JSON.stringify(updated));
      setProfile(updated);
      setMessage('Profile updated successfully.');
      setEditing(false);
    } catch (err: any) {
      setMessage(err.message || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>Loading profile...</span></div>;
  if (error) return <div className="page-error">Error: {error}</div>;

  return (
    <div className="citizen-profile-page">
      <Header title="My Profile" subtitle="Manage your account details" />
      <div className="page-content">
        <div className="profile-card glass-card">
          <div className="profile-header">
            <div className="avatar">{profile?.full_name?.charAt(0)?.toUpperCase() || 'U'}</div>
            <div className="profile-title">
              <h2>{profile?.full_name || 'User'}</h2>
              <span className="role-badge">{profile?.role}</span>
            </div>
            {!editing && (
              <button className="edit-btn" onClick={() => setEditing(true)}><Edit3 size={18} /> Edit</button>
            )}
          </div>

          {message && <div className="message-banner success">{message}</div>}

          <div className="profile-fields">
            <div className="field">
              <label><User size={16} /> Full Name</label>
              {editing ? (
                <input value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} />
              ) : (
                <span>{profile?.full_name || '—'}</span>
              )}
            </div>
            <div className="field">
              <label><Mail size={16} /> Email</label>
              {editing ? (
                <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
              ) : (
                <span>{profile?.email || '—'}</span>
              )}
            </div>
            <div className="field">
              <label><Phone size={16} /> Phone</label>
              {editing ? (
                <input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} />
              ) : (
                <span>{profile?.phone || '—'}</span>
              )}
            </div>
            <div className="field">
              <label><MapPin size={16} /> District</label>
              {editing ? (
                <input value={form.district} onChange={e => setForm({ ...form, district: e.target.value })} />
              ) : (
                <span>{profile?.district || '—'}</span>
              )}
            </div>
            <div className="field">
              <label><Shield size={16} /> Ward</label>
              {editing ? (
                <input value={form.ward} onChange={e => setForm({ ...form, ward: e.target.value })} />
              ) : (
                <span>{profile?.ward || '—'}</span>
              )}
            </div>
          </div>

          {editing && (
            <div className="edit-actions">
              <button className="save-btn" onClick={handleSave} disabled={saving}><Save size={18} /> {saving ? 'Saving...' : 'Save Changes'}</button>
              <button className="cancel-btn" onClick={() => setEditing(false)} disabled={saving}><X size={18} /> Cancel</button>
            </div>
          )}
        </div>

        <div className="info-card glass-card">
          <h3>About Your Account</h3>
          <p>As a Citizen, you can submit grievances, track their status, and view AI-powered classification and duplicate detection results.</p>
        </div>
      </div>
    </div>
  );
};

export default CitizenProfile;
