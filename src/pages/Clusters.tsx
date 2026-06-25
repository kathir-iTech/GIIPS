import { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import type { Incident, ClusterDetail } from '../types';
import Header from '../components/Header';
import './Clusters.css';

const Clusters = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [clusterDetail, setClusterDetail] = useState<ClusterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getIncidents().then(data => {
      setIncidents(data);
      if (data.length > 0) setSelectedId(data[0].id);
    }).catch(err => setError(err.message)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedId) {
      setDetailLoading(true);
      api.getClusterDetail(selectedId).then(setClusterDetail).finally(() => setDetailLoading(false));
    }
  }, [selectedId]);

  if (loading) return <div className="page-loading">Loading clusters...</div>;
  if (error) return <div className="page-error">Error: {error}</div>;

  const networkData = clusterDetail ? {
    nodes: [
      { id: clusterDetail.incident_id, label: clusterDetail.incident_number, isCenter: true },
      ...clusterDetail.complaints.map(c => ({ id: c.id, label: c.complaint_number, isCenter: false }))
    ],
    links: clusterDetail.complaints.map(c => ({ source: clusterDetail.incident_id, target: c.id, similarity: c.similarity_score }))
  } : { nodes: [], links: [] };

  return (
    <div className="clusters-page">
      <Header title="Cluster Explorer" subtitle="Visualize complaint clustering relationships" />
      <div className="page-content">
        <div className="cluster-selector">
          <label htmlFor="incident-select">Select Incident:</label>
          <select id="incident-select" value={selectedId} onChange={e => setSelectedId(e.target.value)}>
            {incidents.map(i => <option key={i.id} value={i.id}>{i.incident_number} - {i.category} ({i.ward})</option>)}
          </select>
        </div>

        {detailLoading ? <div className="page-loading">Loading cluster...</div> : clusterDetail && (
          <div className="cluster-content">
            <div className="cluster-info">
              <div className="info-card">
                <h3>Incident Details</h3>
                <div className="info-grid">
                  <div className="info-item"><span className="info-label">Incident ID</span><span className="info-value">{clusterDetail.incident_number}</span></div>
                  <div className="info-item"><span className="info-label">Category</span><span className="info-value">{clusterDetail.category}</span></div>
                  <div className="info-item"><span className="info-label">Ward</span><span className="info-value">{clusterDetail.ward}</span></div>
                  <div className="info-item"><span className="info-label">Cluster Size</span><span className="info-value">{clusterDetail.cluster_size} complaints</span></div>
                  <div className="info-item"><span className="info-label">Similarity Threshold</span><span className="info-value">{(clusterDetail.similarity_threshold * 100).toFixed(0)}%</span></div>
                </div>
                {clusterDetail.clusterReasoning && <p className="cluster-reasoning">{clusterDetail.clusterReasoning}</p>}
              </div>
            </div>

            <div className="network-diagram">
              <h3>Cluster Network</h3>
              <Plot
                data={[{
                  type: 'sankey',
                  node: {
                    label: networkData.nodes.map(n => n.label),
                    color: networkData.nodes.map(n => n.isCenter ? '#1e293b' : '#94a3b8'),
                    pad: 15,
                    thickness: networkData.nodes.map(n => n.isCenter ? 40 : 15),
                    line: { color: '#e2e8f0', width: 1 }
                  },
                  link: {
                    source: networkData.links.map(() => 0),
                    target: networkData.links.map((_, i) => i + 1),
                    value: networkData.links.map(l => l.similarity),
                    color: networkData.links.map(l => `rgba(30, 41, 59, ${l.similarity * 0.6 + 0.2})`)
                  }
                }]}
                layout={{ paper_bgcolor: 'transparent', margin: { t: 20, r: 20, b: 20, l: 20 }, height: 350 }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>

            <div className="complaints-table-section">
              <h3>Linked Complaints</h3>
              <table className="cluster-complaints-table">
                <thead>
                  <tr>
                    <th>Complaint ID</th>
                    <th>Date Received</th>
                    <th>Similarity Score</th>
                    <th>Text</th>
                  </tr>
                </thead>
                <tbody>
                  {clusterDetail.complaints.map(c => (
                    <tr key={c.id}>
                      <td className="complaint-id">{c.complaint_number}</td>
                      <td>{c.date_received}</td>
                      <td>
                        <div className="similarity-bar-container">
                          <div className="similarity-bar" style={{ width: `${c.similarity_score * 100}%` }}></div>
                          <span className="similarity-text">{(c.similarity_score * 100).toFixed(1)}%</span>
                        </div>
                      </td>
                      <td className="complaint-text">{c.text}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Clusters;
