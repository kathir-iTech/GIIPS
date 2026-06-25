import { useState, useEffect, useMemo } from 'react';
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
  const [sortBy, setSortBy] = useState<'date' | 'similarity'>('similarity');

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

  const sortedComplaints = useMemo(() => {
    if (!clusterDetail) return [];
    const complaints = [...clusterDetail.complaints];
    if (sortBy === 'similarity') complaints.sort((a, b) => b.similarity_score - a.similarity_score);
    else complaints.sort((a, b) => b.date_received.localeCompare(a.date_received));
    return complaints;
  }, [clusterDetail, sortBy]);

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>Loading clusters...</span></div>;
  if (error) return <div className="page-error">Error: {error}</div>;

  const selectedIncident = incidents.find(i => i.id === selectedId);
  const avgSimilarity = clusterDetail ? clusterDetail.complaints.reduce((sum, c) => sum + c.similarity_score, 0) / clusterDetail.complaints.length : 0;

  return (
    <div className="clusters-page">
      <Header title="Cluster Explorer" subtitle="Visualize complaint clustering relationships" />
      <div className="page-content">
        <div className="cluster-controls">
          <div className="incident-selector">
            <label>Select Incident to Explore</label>
            <select value={selectedId} onChange={e => setSelectedId(e.target.value)}>
              {incidents.map(i => <option key={i.id} value={i.id}>{i.incident_number} - {i.category}</option>)}
            </select>
          </div>
          <div className="sort-toggle">
            <label>Sort By</label>
            <div className="toggle-btns">
              <button className={sortBy === 'similarity' ? 'active' : ''} onClick={() => setSortBy('similarity')}>Similarity</button>
              <button className={sortBy === 'date' ? 'active' : ''} onClick={() => setSortBy('date')}>Date</button>
            </div>
          </div>
        </div>

        {detailLoading ? <div className="page-loading"><div className="spinner"></div></div> : clusterDetail && (
          <div className="cluster-content">
            <div className="cluster-header-section">
              <div className="cluster-badge-area">
                <span className="cluster-size-badge">{clusterDetail.cluster_size} Complaints Merged</span>
                <span className="cluster-category">{clusterDetail.category}</span>
              </div>
              <h2 className="cluster-title">{clusterDetail.incident_number}</h2>
              <p className="cluster-location">{clusterDetail.ward}</p>
            </div>

            <div className="cluster-stats-row">
              <div className="stat-card"><span className="stat-value">{(avgSimilarity * 100).toFixed(1)}%</span><span className="stat-label">Avg Similarity</span></div>
              <div className="stat-card"><span className="stat-value">{(clusterDetail.similarity_threshold * 100).toFixed(0)}%</span><span className="stat-label">Threshold</span></div>
              <div className="stat-card"><span className="stat-value">{sortedComplaints.filter(c => c.similarity_score >= 0.9).length}</span><span className="stat-label">High Confidence</span></div>
              <div className="stat-card"><span className="stat-value">{sortedComplaints.length}</span><span className="stat-label">Total Merged</span></div>
            </div>

            <div className="cluster-main">
              <div className="network-section">
                <div className="network-header">
                  <h3>Clustering Visualization</h3>
                  <p className="network-desc">Visual representation of complaint relationships based on semantic similarity</p>
                </div>
                <Plot
                  data={[{
                    type: 'sankey',
                    node: {
                      label: [clusterDetail.incident_number, ...sortedComplaints.slice(0, 8).map(c => c.complaint_number.replace('CMP-', ''))],
                      color: ['#1e293b', ...sortedComplaints.slice(0, 8).map(c => c.similarity_score >= 0.9 ? '#16a34a' : c.similarity_score >= 0.8 ? '#ca8a04' : '#94a3b8')],
                      pad: 20, thickness: 25, line: { color: '#f1f5f9', width: 2 }
                    },
                    link: { source: [0, 0, 0, 0, 0, 0, 0, 0, 0], target: [1, 2, 3, 4, 5, 6, 7, 8, 9], value: sortedComplaints.slice(0, 8).map(c => c.similarity_score), color: sortedComplaints.slice(0, 8).map(c => `rgba(30, 41, 59, ${c.similarity_score * 0.5 + 0.15})`) }
                  }]}
                  layout={{ paper_bgcolor: 'transparent', margin: { t: 40, r: 40, b: 40, l: 40 }, height: 320, font: { family: 'Inter, sans-serif', size: 11 } }}
                  config={{ displayModeBar: false, responsive: true }}
                  style={{ width: '100%' }}
                />
              </div>

              <div className="reasoning-section">
                <h3>Why These Complaints Belong Together</h3>
                <div className="reasoning-content">
                  <div className="reasoning-point"><span className="point-dot location"></span><span className="point-text">All complaints reference the same geographic location ({clusterDetail.ward.split(' - ')[1] || 'local area'})</span></div>
                  <div className="reasoning-point"><span className="point-dot category"></span><span className="point-text">Related to the same issue category: {clusterDetail.category}</span></div>
                  <div className="reasoning-point"><span className="point-dot time"></span><span className="point-text">Complaints received within a similar time frame</span></div>
                  <div className="reasoning-point"><span className="point-dot semantic"></span><span className="point-text">Semantic analysis indicates {(avgSimilarity * 100).toFixed(0)}% text similarity</span></div>
                </div>
                {selectedIncident && <p className="cluster-summary">{selectedIncident.summary}</p>}
              </div>
            </div>

            <div className="complaints-section">
              <div className="complaints-header"><h3>Linked Complaints Timeline</h3><span className="complaints-count">{sortedComplaints.length} complaints</span></div>
              <div className="timeline">
                {sortedComplaints.map((c, i) => (
                  <div key={c.id} className="timeline-item">
                    <div className="timeline-marker"><span className="marker-num">{i + 1}</span></div>
                    <div className="timeline-content">
                      <div className="timeline-header"><span className="timeline-id">{c.complaint_number}</span><span className="timeline-date">{c.date_received}</span></div>
                      <p className="timeline-text">{c.text}</p>
                      <div className="timeline-meta">
                        <div className="similarity-meter"><div className="meter-fill" style={{ width: `${c.similarity_score * 100}%` }}></div></div>
                        <span className="similarity-value">{(c.similarity_score * 100).toFixed(1)}% match</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Clusters;
