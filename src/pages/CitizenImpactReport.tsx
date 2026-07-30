import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { TrendingUp, Users, DollarSign, AlertTriangle } from 'lucide-react';
import Header from '../components/Header';

const CitizenImpactReport = () => {
  const { t } = useTranslation();
  const [complaints, setComplaints] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getMyComplaints()
      .then(d => setComplaints(Array.isArray(d) ? d : []))
      .catch(() => setComplaints([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-container"><Header title={t('citizenImpact.title')} /><p className="loading-text">{t('common.loading')}</p></div>;

  const totalFiled = complaints.length;
  const resolved = complaints.filter((c: any) => c.incident?.status === 'resolved');
  const totalImpact = resolved.reduce((s: number, c: any) => s + (c.incident?.impact_score || 0), 0);
  const totalEconomic = resolved.reduce((s: number, c: any) => s + (c.incident?.economic_impact || 0), 0);

  return (
    <div className="page-container">
      <Header title={t('citizenImpact.title')} subtitle={t('citizenImpact.subtitle')} />
      {totalFiled === 0 ? (
        <div className="empty-state"><AlertTriangle size={24} /><p>{t('citizenImpact.empty')}</p></div>
      ) : (
        <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: '2rem' }}>
          <div className="kpi-card"><TrendingUp size={24} /><h3>{totalFiled}</h3><p>{t('citizenImpact.totalFiled')}</p></div>
          <div className="kpi-card"><Users size={24} /><h3>{totalImpact.toFixed(0)}</h3><p>{t('citizenImpact.peopleHelped')}</p></div>
          <div className="kpi-card"><DollarSign size={24} /><h3>₹{totalEconomic.toFixed(0)}</h3><p>{t('citizenImpact.economicValue')}</p></div>
        </div>
      )}
    </div>
  );
};
export default CitizenImpactReport;
