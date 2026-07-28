import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, BookOpen } from 'lucide-react';
import './ApiDocs.css';

const ENDPOINTS = [
  { method: 'GET', path: '/public/stats', auth: 'No', descKey: 'apiDocs.descStats' },
  { method: 'GET', path: '/public/track/{id}', auth: 'No', descKey: 'apiDocs.descTrack' },
  { method: 'GET', path: '/public/nearby-complaints', auth: 'No', params: 'ward, category, exclude', descKey: 'apiDocs.descNearby' },
  { method: 'GET', path: '/public/success-stories', auth: 'No', params: '?ward=', descKey: 'apiDocs.descStories' },
  { method: 'GET', path: '/public/word-cloud', auth: 'No', descKey: 'apiDocs.descWordCloud' },
  { method: 'GET', path: '/public/satisfaction-trend', auth: 'No', descKey: 'apiDocs.descSatisfaction' },
  { method: 'GET', path: '/public/ward-stats/{ward}', auth: 'No', descKey: 'apiDocs.descWardStats' },
];

const exampleResponses: Record<string, string> = {
  '/public/stats': JSON.stringify({ totalComplaints: 1250, totalIncidents: 340, avgResolutionDays: 3.2 }, null, 2),
  '/public/track/{id}': JSON.stringify({ id: 'COMP-000001', status: 'resolved', category: 'Roads', timeline: [{ status: 'open', date: '2026-07-20T10:00:00Z' }, { status: 'resolved', date: '2026-07-25T14:30:00Z' }] }, null, 2),
  '/public/nearby-complaints': JSON.stringify([{ complaint_id: 'COMP-000002', status: 'open', priority: 'High', ward: '27', days_open: 5 }], null, 2),
  '/public/success-stories': JSON.stringify([{ complaint_id: 'COMP-000010', title: 'Road pothole fixed', rating: 5, resolved_at: '2026-07-24T09:00:00Z' }], null, 2),
  '/public/word-cloud': JSON.stringify({ words: [{ text: 'pothole', count: 89 }, { text: 'water', count: 72 }] }, null, 2),
  '/public/satisfaction-trend': JSON.stringify({ weeks: ['2026-06-07', '2026-06-14'], avgRating: [4.2, 4.5] }, null, 2),
  '/public/ward-stats/{ward}': JSON.stringify({ ward: '27', totalComplaints: 45, openIncidents: 12, topCategory: 'Roads' }, null, 2),
};

const ApiDocs = () => {
  const { t } = useTranslation();
  return (
    <div className="api-docs-page">
      <div className="api-docs-header">
        <Link to="/" className="api-back-link"><ArrowLeft size={16} /> {t('apiDocs.backToHome')}</Link>
        <h1><BookOpen size={24} /> {t('apiDocs.title')}</h1>
        <p className="api-subtitle">{t('apiDocs.subtitle')}</p>
      </div>
      <div className="api-docs-content">
        <table className="api-endpoints-table">
          <thead>
            <tr>
              <th>{t('apiDocs.colMethod')}</th>
              <th>{t('apiDocs.colEndpoint')}</th>
              <th>{t('apiDocs.colAuth')}</th>
              <th>{t('apiDocs.colParams')}</th>
              <th>{t('apiDocs.colDescription')}</th>
              <th>{t('apiDocs.colExample')}</th>
            </tr>
          </thead>
          <tbody>
            {ENDPOINTS.map((ep, i) => (
              <tr key={i}>
                <td><span className={`method-badge method-${ep.method.toLowerCase()}`}>{ep.method}</span></td>
                <td><code className="endpoint-path">{ep.path}</code></td>
                <td><span className={`auth-badge ${ep.auth === 'No' ? 'auth-no' : 'auth-yes'}`}>{ep.auth === 'No' ? t('apiDocs.noAuth') : ep.auth}</span></td>
                <td>{(ep as any).params || t('apiDocs.emDash')}</td>
                <td>{t(ep.descKey)}</td>
                <td><pre className="example-response"><code>{exampleResponses[ep.path]}</code></pre></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ApiDocs;
