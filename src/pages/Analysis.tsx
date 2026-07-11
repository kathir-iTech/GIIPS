import { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import type { ClassificationMetrics } from '../types';
import Header from '../components/Header';
import './Analysis.css';

const qualityClass = (value: number) => value >= 0.9 ? 'excellent' : value >= 0.8 ? 'good' : value >= 0.7 ? 'warning' : 'poor';

const Analysis = () => {
  const [metrics, setMetrics] = useState<ClassificationMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getClassificationMetrics()
      .then(data => { if (!cancelled) setMetrics(data); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>Loading analysis...</span></div>;
  if (error) return <div className="page-error">Error: {error}</div>;
  if (!metrics) return null;

  const categoryData = metrics.categoryDistribution;
  const confusionData = metrics.confusionMatrix;
  const hasConfusion = confusionData && confusionData.length > 0;
  const hasCategories = metrics.categories && metrics.categories.length > 0;

  return (
    <div className="analysis-page">
      <Header title="Complaint Analysis" subtitle="Model performance and classification metrics" />
      <div className="page-content">
        <section className="model-info">
          <div className="model-badge">
            <span className="model-icon">AI</span>
            <span className="model-name">{metrics.modelType}</span>
          </div>
          <div className="dataset-info">
            <span className="dataset-label">Dataset Size</span>
            <span className="dataset-value">{(metrics.datasetSize ?? 0).toLocaleString()} complaints</span>
          </div>
        </section>

        <section className="metrics-hero">
          <div className="metric-card primary">
            <div className="metric-header">
              <span className="metric-title">Accuracy</span>
              <div className={`metric-indicator ${qualityClass(metrics.accuracy)}`}></div>
            </div>
            <span className="metric-value">{(metrics.accuracy * 100).toFixed(1)}%</span>
            <p className="metric-desc">Overall classification correctness across all categories</p>
          </div>
          <div className="metric-card primary">
            <div className="metric-header">
              <span className="metric-title">Precision</span>
              <div className={`metric-indicator ${qualityClass(metrics.precision)}`}></div>
            </div>
            <span className="metric-value">{(metrics.precision * 100).toFixed(1)}%</span>
            <p className="metric-desc">True positives among predicted cluster memberships</p>
          </div>
          <div className="metric-card primary">
            <div className="metric-header">
              <span className="metric-title">Recall</span>
              <div className={`metric-indicator ${qualityClass(metrics.recall)}`}></div>
            </div>
            <span className="metric-value">{(metrics.recall * 100).toFixed(1)}%</span>
            <p className="metric-desc">Actual duplicates correctly identified by model</p>
          </div>
          <div className="metric-card primary">
            <div className="metric-header">
              <span className="metric-title">F1 Score</span>
              <div className={`metric-indicator ${qualityClass(metrics.f1Score)}`}></div>
            </div>
            <span className="metric-value">{(metrics.f1Score * 100).toFixed(1)}%</span>
            <p className="metric-desc">Harmonic mean balancing precision and recall</p>
          </div>
        </section>

        <section className="charts-section">
          <div className="chart-card large">
            <div className="chart-header">
              <h3>Complaint & Incident Volume (6 Months)</h3>
              <span className="chart-subtitle">Monthly totals from backend</span>
            </div>
            {metrics.trendData.length > 0 ? (
              <Plot
                data={[
                  { x: metrics.trendData.map(d => d.month), y: metrics.trendData.map(d => d.complaints), type: 'scatter', mode: 'lines+markers', name: 'Complaints', line: { color: '#1e293b', width: 3 }, marker: { size: 8 } },
                  { x: metrics.trendData.map(d => d.month), y: metrics.trendData.map(d => d.incidents), type: 'scatter', mode: 'lines+markers', name: 'Incidents', line: { color: '#0369a1', width: 2, dash: 'dot' }, marker: { size: 6 } },
                ]}
                layout={{
                  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
                  margin: { t: 10, r: 30, b: 50, l: 60 },
                  xaxis: { showgrid: false, tickangle: -45 },
                  yaxis: { showgrid: true, gridcolor: '#f1f5f9' },
                  showlegend: true, legend: { orientation: 'h', y: 1.15 },
                  hovermode: 'x unified', height: 300
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            ) : (
              <div className="empty-chart">No trend data available.</div>
            )}
          </div>

          <div className="chart-card">
            <div className="chart-header"><h3>Category Distribution</h3><span className="chart-subtitle">Complaints by issue type</span></div>
            {categoryData.length > 0 ? (
              <Plot
                data={[{
                  values: categoryData.map(d => d.count),
                  labels: categoryData.map(d => d.category),
                  type: 'pie',
                  hole: 0.45,
                  marker: { colors: ['#1e293b', '#0369a1', '#7c3aed', '#b45309', '#059669', '#be123c'] },
                  textinfo: 'value+percent',
                  textposition: 'outside',
                  textfont: { size: 11 }
                }]}
                layout={{
                  paper_bgcolor: 'transparent',
                  margin: { t: 30, r: 30, b: 80, l: 30 },
                  showlegend: true,
                  legend: { orientation: 'h', y: -0.15 },
                  annotations: [{ text: 'Total', showarrow: false, font: { size: 14, weight: 600 }, y: 0.55 }],
                  height: 300
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            ) : (
              <div className="empty-chart">No category distribution available.</div>
            )}
          </div>

          <div className="chart-card">
            <div className="chart-header"><h3>Confidence Matrix</h3><span className="chart-subtitle">Clustering accuracy heatmap</span></div>
            {hasConfusion && hasCategories ? (
              <Plot
                data={[{
                  z: confusionData.slice(0, 4).map(row => row.slice(0, 4)),
                  x: metrics.categories.slice(0, 4).map(c => c.split(' ')[0]),
                  y: metrics.categories.slice(0, 4).map(c => c.split(' ')[0]),
                  type: 'heatmap',
                  colorscale: [[0, '#f1f5f9'], [1, '#1e293b']],
                  showscale: false
                }]}
                layout={{
                  paper_bgcolor: 'transparent',
                  margin: { t: 10, r: 30, b: 60, l: 80 },
                  xaxis: { side: 'bottom' },
                  yaxis: { autorange: 'reversed' },
                  height: 280
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            ) : (
              <div className="empty-chart">Confusion matrix data not available.</div>
            )}
          </div>

        </section>
      </div>
    </div>
  );
};

export default Analysis;
