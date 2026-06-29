import React, { useEffect, useState } from 'react';
import Plot from 'react-plotly.js';
import { api } from '../services/api';
import Header from '../components/Header';
import './SpatialIntelligence.css';

const SpatialIntelligence = () => {
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [forecast, setForecast] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getHeatmap(), api.getForecast(7)])
      .then(([h, f]) => {
        setHeatmap(h);
        setForecast(f);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading spatial data...</div>;

  return (
    <div className="spatial-page">
      <Header title="Spatial Intelligence" subtitle="Geospatial analysis of municipal incidents" />
      <div className="page-content">
        <section className="spatial-grid">
          <div className="card">
            <h3>Incident Distribution</h3>
            <Plot
              data={[{
                labels: heatmap.map(d => d.ward),
                values: heatmap.map(d => d.count),
                type: 'pie',
              }]}
              layout={{ title: 'Incidents per Ward', height: 300, margin: { t: 40, b: 0 } }}
              style={{ width: '100%' }}
            />
          </div>
          <div className="card">
            <h3>Forecasted Incidents</h3>
            <Plot
              data={[{
                x: forecast.map(d => d.date),
                y: forecast.map(d => d.forecast),
                type: 'scatter',
                mode: 'lines+markers',
                marker: { color: '#3b82f6' }
              }]}
              layout={{ title: '7-Day Forecast', height: 300, margin: { t: 40, b: 40 } }}
              style={{ width: '100%' }}
            />
          </div>
        </section>
      </div>
    </div>
  );
};
export default SpatialIntelligence;
