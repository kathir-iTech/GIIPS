import { useState, useEffect, useMemo } from 'react';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import type { Incident, ClusterDetail } from '../types';
import Header from '../components/Header';
import KPICard from '../components/KPICard';
import { Target, GitBranch, AlertTriangle } from 'lucide-react';
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
      setError(null);
      api.getClusterDetail(selectedId)
        .then(setClusterDetail)
        .catch(err => setError(err.message))
        .finally(() => setDetailLoading(false));
    }
  }, [selectedId]);

  if (loading) return <div className="page-loading">Loading cluster data...</div>;
  if (error && !clusterDetail) return <div className="page-error">Error: {error}</div>;

  const complaints = clusterDetail?.complaints ?? [];
  const avgSimilarity = complaints.length > 0 ? complaints.reduce((sum, c) => sum + (c.similarity_score || 0), 0) / complaints.length : 0;

  const sankeyData = useMemo(() => {
    const maxNodes = Math.min(complaints.length, 5);
    const labels = [clusterDetail?.incident_number || 'Incident', ...complaints.slice(0, maxNodes).map(c => c.complaint_number)];
    const colors = ['#1e293b', ...Array(maxNodes).fill('#0369a1')];
    const source = Array(maxNodes).fill(0);
    const target = Array.from({ length: maxNodes }, (_, i) => i + 1);
    const values = complaints.slice(0, maxNodes).map(c => Math.max(c.similarity_score || 0.01, 0.01));

    return {
      type: 'sankey',
      node: { label: labels, color: colors, pad: 20, thickness: 20 },
      link: { source, target, value: values }
    };
  }, [clusterDetail, complaints]);

  return (
    <div className="clusters-page">
      <Header title="Cluster Explorer" subtitle="Analyze AI-driven incident grouping" />
      <div className="page-content">
        <div className="cluster-controls">
          <select value={selectedId} onChange={e => setSelectedId(e.target.value)}>
            {(incidents ?? []).map(i => <option key={i.id} value={i.id}>{i.incident_number} - {i.category}</option>)}
          </select>
        </div>

        {error && <div className="page-error">Failed to load cluster detail: {error}</div>}

        {detailLoading ? <div className="page-loading">Refreshing cluster details...</div> : clusterDetail && (
          <div className="cluster-content">
            <section className="cluster-header-section">
              <h2 className="cluster-title">{clusterDetail.incident_number}</h2>
              <p className="cluster-location">{clusterDetail.category} • {clusterDetail.ward}</p>
            </section>

            <section className="cluster-stats-row">
              <KPICard title="Complaints Merged" value={clusterDetail.cluster_size} icon={GitBranch} />
              <KPICard title="Avg Similarity" value={`${(avgSimilarity * 100).toFixed(1)}%`} icon={Target} />
              <KPICard title="Confidence" value="High" icon={AlertTriangle} variant="success" />
            </section>

            <section className="cluster-main">
              <div className="card">
                <h3>Clustering Visualization</h3>
                {complaints.length > 0 ? (
                  <Plot
                    data={[sankeyData]}
                    layout={{ paper_bgcolor: 'transparent', margin: { t: 20, r: 20, b: 20, l: 20 }, height: 250 }}
                    config={{ displayModeBar: false, responsive: true }}
                    style={{ width: '100%' }}
                  />
                ) : (
                  <div className="empty-chart">No complaints linked to this cluster for visualization.</div>
                )}
              </div>
              <div className="card">
                <h3>AI Reasoning</h3>
                <p>{clusterDetail.clusterReasoning ?? 'No AI reasoning available for this cluster.'}</p>
              </div>
            </section>

            <section className="card">
              <h3>Complaint Timeline</h3>
              {complaints.length > 0 ? (
                <div className="timeline">
                  {complaints.map((c, i) => (
                    <div key={c.id} className="timeline-item">
                      <div className="timeline-marker">{i + 1}</div>
                      <div className="timeline-content">
                        <strong>{c.complaint_number}</strong>
                        <p>{c.text}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">No complaints in timeline.</div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
};

export default Clusters;
