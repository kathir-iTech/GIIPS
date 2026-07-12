import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { Server, Database, Brain, Shield, Clock, Users, MessageSquare, Activity } from 'lucide-react';
import './Admin.css';

const SystemHealth = () => {
  const { t } = useTranslation();
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth();
  }, []);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/admin/system-health');
      const data = await response.json();
      setHealth(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('systemHealth.loadError'));
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>{t('systemHealth.loading')}</span></div>;
  if (error) return <div className="page-error">{t('systemHealth.errorPrefix')}{error}</div>;
  if (!health) return <div className="page-error">{t('systemHealth.noData')}</div>;

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>{t('systemHealth.header.title')}</h1>
        <p>{t('systemHealth.header.subtitle')}</p>
      </div>

      <div className="health-grid">
        <div className="health-card">
          <Server size={24} />
          <div className="health-info">
            <h3>{t('systemHealth.card.backend')}</h3>
            <span className={`status ${health?.backend || 'unknown'}`}>{(health?.backend || 'unknown').toUpperCase()}</span>
          </div>
        </div>

        <div className="health-card">
          <Database size={24} />
          <div className="health-info">
            <h3>{t('systemHealth.card.database')}</h3>
            <span className={`status ${health?.database || 'unknown'}`}>{(health?.database || 'unknown').toUpperCase()}</span>
          </div>
        </div>

        <div className="health-card">
          <Brain size={24} />
          <div className="health-info">
            <h3>{t('systemHealth.card.aiEngine')}</h3>
            <span className={`status ${health?.ai_engine || 'unknown'}`}>{(health?.ai_engine || 'unknown').toUpperCase()}</span>
          </div>
        </div>

        <div className="health-card">
          <Shield size={24} />
          <div className="health-info">
            <h3>{t('systemHealth.card.jwtAuth')}</h3>
            <span className={`status ${health?.jwt_auth || 'unknown'}`}>{(health?.jwt_auth || 'unknown').toUpperCase()}</span>
          </div>
        </div>

        <div className="health-card">
          <Brain size={24} />
          <div className="health-info">
            <h3>{t('systemHealth.card.classification')}</h3>
            <span className={`status ${health?.classification_model || 'unknown'}`}>{(health?.classification_model || 'unknown').toUpperCase()}</span>
          </div>
        </div>

        <div className="health-card">
          <Activity size={24} />
          <div className="health-info">
            <h3>{t('systemHealth.card.prediction')}</h3>
            <span className={`status ${health?.prediction_engine || 'unknown'}`}>{(health?.prediction_engine || 'unknown').toUpperCase()}</span>
          </div>
        </div>

        <div className="health-card">
          <Database size={24} />
          <div className="health-info">
            <h3>{t('systemHealth.card.duplicateDetection')}</h3>
            <span className={`status ${health?.duplicate_detection || 'unknown'}`}>{(health?.duplicate_detection || 'unknown').toUpperCase()}</span>
          </div>
        </div>

        <div className="health-card">
          <MessageSquare size={24} />
          <div className="health-info">
            <h3>{t('systemHealth.card.knowledgeEngine')}</h3>
            <span className={`status ${health?.knowledge_engine || 'unknown'}`}>{(health?.knowledge_engine || 'unknown').toUpperCase()}</span>
          </div>
        </div>

        <div className="health-card">
          <Users size={24} />
          <div className="health-info">
            <h3>{t('systemHealth.card.decisionEngine')}</h3>
            <span className={`status ${health?.decision_engine || 'unknown'}`}>{(health?.decision_engine || 'unknown').toUpperCase()}</span>
          </div>
        </div>
      </div>

      <div className="metrics-section">
        <h2>{t('systemHealth.metrics.title')}</h2>
        <div className="metrics-grid">
          <div className="metric-card">
            <h3>{health?.users || 0}</h3>
            <p>{t('systemHealth.metrics.totalUsers')}</p>
          </div>
          <div className="metric-card">
            <h3>{health?.complaints || 0}</h3>
            <p>{t('systemHealth.metrics.totalComplaints')}</p>
          </div>
          <div className="metric-card">
            <h3>{health?.incidents || 0}</h3>
            <p>{t('systemHealth.metrics.totalIncidents')}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemHealth;