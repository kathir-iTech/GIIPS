import { Link } from 'react-router-dom';
import { ArrowLeft, BookOpen } from 'lucide-react';
import './ApiDocs.css';

const ENDPOINTS = [
  { method: 'GET', path: '/public/stats', auth: 'No', desc: 'Aggregate complaint statistics for the public dashboard.' },
  { method: 'GET', path: '/public/track/{id}', auth: 'No', desc: 'Track a single complaint by its ID. Returns status, timeline, resolution.' },
  { method: 'GET', path: '/public/nearby-complaints', auth: 'No', params: 'ward, category, exclude', desc: 'Find nearby complaints by ward and category.' },
  { method: 'GET', path: '/public/success-stories', auth: 'No', params: '?ward=', desc: 'Resolved complaints with positive citizen ratings.' },
  { method: 'GET', path: '/public/word-cloud', auth: 'No', desc: 'Top 30 most frequent words in complaint descriptions.' },
  { method: 'GET', path: '/public/satisfaction-trend', auth: 'No', desc: 'Weekly average citizen rating over the last 8 weeks.' },
  { method: 'GET', path: '/public/ward-stats/{ward}', auth: 'No', desc: 'Complaint statistics for a specific ward.' },
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
  return (
    <div className="api-docs-page">
      <div className="api-docs-header">
        <Link to="/" className="api-back-link"><ArrowLeft size={16} /> Back to Home</Link>
        <h1><BookOpen size={24} /> GIIPS Public API Documentation</h1>
        <p className="api-subtitle">Open endpoints for public dashboards, tracking, and transparency — no authentication required.</p>
      </div>
      <div className="api-docs-content">
        <table className="api-endpoints-table">
          <thead>
            <tr>
              <th>Method</th>
              <th>Endpoint</th>
              <th>Auth</th>
              <th>Parameters</th>
              <th>Description</th>
              <th>Example Response</th>
            </tr>
          </thead>
          <tbody>
            {ENDPOINTS.map((ep, i) => (
              <tr key={i}>
                <td><span className={`method-badge method-${ep.method.toLowerCase()}`}>{ep.method}</span></td>
                <td><code className="endpoint-path">{ep.path}</code></td>
                <td><span className={`auth-badge ${ep.auth === 'No' ? 'auth-no' : 'auth-yes'}`}>{ep.auth}</span></td>
                <td>{(ep as any).params || '—'}</td>
                <td>{ep.desc}</td>
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
