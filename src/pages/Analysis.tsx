import { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import type { ClassificationMetrics } from '../types';
import Header from '../components/Header';
import './Analysis.css';

const Analysis = () => {
  const [metrics, setMetrics] = useState<ClassificationMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getClassificationMetrics().then(setMetrics).catch(err => setError(err.message)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading analysis...</div>;
  if (error) return <div className="page-error">Error: {error}</div>;
  if (!metrics) return null;

  const categoryData = metrics.categoryDistribution;
  const confusionData = metrics.confusionMatrix;

  return (
    <div className="analysis-page">
      <Header title="Complaint Analysis" subtitle="Model performance and classification metrics" />
      <div className="page-content">
        <section className="metrics-section">
          <div className="metrics-grid">
            <div className="metric-card"><span className="metric-value">{(metrics.accuracy * 100).toFixed(1)}%</span><span className="metric-label">Accuracy</span></div>
            <div className="metric-card"><span className="metric-value">{(metrics.precision * 100).toFixed(1)}%</span><span className="metric-label">Precision</span></div>
            <div className="metric-card"><span className="metric-value">{(metrics.recall * 100).toFixed(1)}%</span><span className="metric-label">Recall</span></div>
            <div className="metric-card"><span className="metric-value">{(metrics.f1Score * 100).toFixed(1)}%</span><span className="metric-label">F1 Score</span></div>
          </div>
        </section>

        <section className="charts-section">
          <div className="chart-card">
            <h3>Category Distribution</h3>
            <Plot data={[{ values: categoryData.map(d => d.count), labels: categoryData.map(d => d.category), type: 'pie', hole: 0.4, marker: { colors: ['#1e293b', '#334155', '#475569', '#64748b', '#94a3b8', '#cbd5e1'] }, textinfo: 'percent', textposition: 'inside' }]}
              layout={{ paper_bgcolor: 'transparent', margin: { t: 20, r: 20, b: 20, l: 20 }, showlegend: true, legend: { orientation: 'h', y: -0.1 } }}
              config={{ displayModeBar: false, responsive: true }} style={{ width: '100%', height: 300 }} />
          </div>

          <div className="chart-card">
            <h3>Confusion Matrix (Similarity Threshold: 0.85)</h3>
            <Plot data={[{ z: confusionData, type: 'heatmap', colorscale: [[0, '#f8fafc'], [1, '#1e293b']], showscale: false, text: confusionData.map((row, i) => row.map((val, j) => val)), texttemplate: '%{text}', textfont: { size: 14 } }]}
              layout={{ paper_bgcolor: 'transparent', margin: { t: 40, r: 20, b: 60, l: 80 }, xaxis: { title: 'Predicted', tickvals: [0, 1], ticktext: ['Different', 'Same'] }, yaxis: { title: 'Actual', tickvals: [0, 1], ticktext: ['Different', 'Same'] }, height: 280 }}
              config={{ displayModeBar: false, responsive: true }} style={{ width: '100%' }} />
          </div>

          <div className="chart-card full-width">
            <h3>Model Performance Trend</h3>
            <Plot data={[
              { x: metrics.trendData.map(d => d.month), y: metrics.trendData.map(d => d.accuracy), type: 'scatter', mode: 'lines+markers', name: 'Accuracy', line: { color: '#1e293b', width: 2 } },
              { x: metrics.trendData.map(d => d.month), y: metrics.trendData.map(d => d.precision), type: 'scatter', mode: 'lines+markers', name: 'Precision', line: { color: '#64748b', width: 2 } },
              { x: metrics.trendData.map(d => d.month), y: metrics.trendData.map(d => d.recall), type: 'scatter', mode: 'lines+markers', name: 'Recall', line: { color: '#94a3b8', width: 2 } }
            ]}
              layout={{ paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', margin: { t: 20, r: 20, b: 40, l: 40 }, xaxis: { title: 'Month', showgrid: false }, yaxis: { title: 'Score', range: [0.85, 1], showgrid: true, gridcolor: '#f1f5f9' }, showlegend: true, legend: { orientation: 'h', y: 1.1 }, height: 280 }}
              config={{ displayModeBar: false, responsive: true }} style={{ width: '100%' }} />
          </div>
        </section>
      </div>
    </div>
  );
};

export default Analysis;
