import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { MapPin, Star, AlertTriangle, ThumbsUp } from 'lucide-react';
import Header from '../components/Header';

const CouncillorPerformance = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCouncillorPerformance()
      .then(d => setData(Array.isArray(d) ? d : []))
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-container"><Header title={t('councillorPerformance.title')} /><p className="loading-text">{t('common.loading')}</p></div>;

  return (
    <div className="page-container">
      <Header title={t('councillorPerformance.title')} subtitle={t('councillorPerformance.subtitle')} />
      {data.length === 0 ? (
        <div className="empty-state"><AlertTriangle size={24} /><p>{t('councillorPerformance.empty')}</p></div>
      ) : (
        <div className="leaderboard-table">
          <div className="leaderboard-header">
            <span>{t('councillorPerformance.name')}</span>
            <span>{t('councillorPerformance.ward')}</span>
            <span>{t('councillorPerformance.open')}</span>
            <span>{t('councillorPerformance.resolved')}</span>
            <span>{t('councillorPerformance.rate')}</span>
            <span>{t('councillorPerformance.rating')}</span>
          </div>
          {data.map((c: any, i: number) => (
            <div key={i} className="leaderboard-row">
              <span className="name-col">{c.councillor_name}</span>
              <span className="ward-col"><MapPin size={12} /> {c.ward}</span>
              <span className="count-col">{c.open_incidents}</span>
              <span className="count-col">{c.resolved_incidents}</span>
              <span className="rate-col">{c.resolution_rate}%</span>
              <span className="rating-col"><Star size={12} fill={c.avg_citizen_rating >= 4 ? '#f59e0b' : '#64748b'} color={c.avg_citizen_rating >= 4 ? '#f59e0b' : '#64748b'} /> {c.avg_citizen_rating}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
export default CouncillorPerformance;
