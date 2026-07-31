import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { ArrowLeft, AlertTriangle, CheckCircle, Layers, Loader2 } from 'lucide-react';
import './Admin.css';

const CATEGORIES = [
  'Roads',
  'Water Supply',
  'Waste Management',
  'Sanitation',
  'Street Lighting',
  'Electricity',
  'Public Health',
];

const AdminTools = () => {
  const { t } = useTranslation();
  const [oldCategory, setOldCategory] = useState('');
  const [newCategory, setNewCategory] = useState('');
  const [migrating, setMigrating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const handleMigrate = async () => {
    setError(null);
    setResult(null);
    if (!oldCategory || !newCategory) {
      setError(t('adminTools.selectOld'));
      return;
    }
    if (oldCategory === newCategory) {
      setError(t('adminTools.sameCategoryError'));
      return;
    }
    setMigrating(true);
    try {
      const res = await api.migrateCategory(oldCategory, newCategory);
      setResult(res || { reclassified: 0 });
    } catch (err: any) {
      setError(err.message || t('adminTools.migrateError'));
    } finally {
      setMigrating(false);
    }
  };

  return (
    <div className="admin-page">
      <div className="page-header">
        <h1><Layers size={22} /> {t('adminTools.title')}</h1>
        <p>{t('adminTools.subtitle')}</p>
      </div>

      <div className="comparison-section" style={{ marginBottom: '1.5rem' }}>
        <div className="form-grid" style={{ marginBottom: '1.5rem' }}>
          <label>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>{t('adminTools.selectOld')}</span>
            <select value={oldCategory} onChange={e => { setOldCategory(e.target.value); setError(null); setResult(null); }} style={{ width: '100%', padding: '0.75rem', borderRadius: 8, border: '1px solid #334155', background: '#1e293b', color: '#e2e8f0' }}>
              <option value="">—</option>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
          <label>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>{t('adminTools.selectNew')}</span>
            <select value={newCategory} onChange={e => { setNewCategory(e.target.value); setError(null); setResult(null); }} style={{ width: '100%', padding: '0.75rem', borderRadius: 8, border: '1px solid #334155', background: '#1e293b', color: '#e2e8f0' }}>
              <option value="">—</option>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
        </div>

        {error && (
          <div className="message-banner error" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0.75rem 1rem', borderRadius: 8, background: 'rgba(220,38,38,0.12)', color: '#f87171', marginBottom: '1rem' }}>
            <AlertTriangle size={16} /> {error}
          </div>
        )}
        {result && (
          <div className="message-banner success" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0.75rem 1rem', borderRadius: 8, background: 'rgba(22,163,74,0.12)', color: '#4ade80', marginBottom: '1rem' }}>
            <CheckCircle size={16} /> {t('adminTools.migrateSuccess')} — {t('adminTools.resultCount', { count: result.reclassified ?? result.count ?? 0 })}
          </div>
        )}

        <button
          className="action-btn"
          onClick={handleMigrate}
          disabled={migrating}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '0.75rem 1.5rem', borderRadius: 8, border: 'none', background: '#3b82f6', color: 'white', fontSize: 14, fontWeight: 600, cursor: migrating ? 'wait' : 'pointer', fontFamily: 'inherit' }}
        >
          {migrating ? <Loader2 size={16} className="spin" /> : <Layers size={16} />} {migrating ? t('adminTools.migrating') : t('adminTools.migrateButton')}
        </button>
      </div>

      <a href="/admin/departments" className="action-btn" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', textDecoration: 'none' }}>
        <ArrowLeft size={14} /> {t('adminTools.backToAdmin')}
      </a>
    </div>
  );
};

export default AdminTools;
