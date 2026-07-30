import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { MapPin, Star, AlertTriangle } from 'lucide-react';
import Header from '../components/Header';
import './CitizenLeaderboard.css';

const CitizenLeaderboard = () => {
  const { t } = useTranslation();
  const [citizens, setCitizens] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCitizenLeaderboard()
      .then(data => {
        if (Array.isArray(data)) setCitizens(data);
        else setCitizens([]);
      })
      .catch(() => setCitizens([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-container">
      <Header title={t('citizenLeaderboard.title')} subtitle={t('citizenLeaderboard.subtitle')} />
      {loading ? (
        <p className="loading-text">{t('common.loading')}</p>
      ) : citizens.length === 0 ? (
        <div className="empty-state">
          <AlertTriangle size={24} />
          <p>{t('citizenLeaderboard.empty')}</p>
        </div>
      ) : (
        <div className="leaderboard-table">
          <div className="leaderboard-header">
            <span className="rank-col">#</span>
            <span className="name-col">{t('citizenLeaderboard.name')}</span>
            <span className="ward-col">{t('citizenLeaderboard.ward')}</span>
            <span className="count-col">{t('citizenLeaderboard.complaints')}</span>
            <span className="rate-col">{t('citizenLeaderboard.resolutionRate')}</span>
            <span className="rating-col">{t('citizenLeaderboard.avgRating')}</span>
          </div>
          {citizens.map((c, i) => (
            <div key={i} className={`leaderboard-row ${i < 3 ? 'top-three' : ''}`}>
              <span className="rank-col">{(i < 3 ? ['🥇', '🥈', '🥉'][i] : `#${i + 1}`)}</span>
              <span className="name-col">{c.name}</span>
              <span className="ward-col"><MapPin size={12} /> {t('citizenLeaderboard.wardPrefix', { ward: c.ward })}</span>
              <span className="count-col">{c.complaint_count}</span>
              <span className="rate-col">{c.resolution_rate}%</span>
              <span className="rating-col"><Star size={12} fill={c.avg_rating >= 4 ? '#f59e0b' : '#64748b'} color={c.avg_rating >= 4 ? '#f59e0b' : '#64748b'} /> {c.avg_rating}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CitizenLeaderboard;
