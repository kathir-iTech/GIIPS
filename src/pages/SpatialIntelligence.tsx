import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { api } from '../services/api';
import { Zap, AlertTriangle, RefreshCw } from 'lucide-react';
import './SpatialIntelligence.css';

const wardLocations: Record<string, [number, number]> = {
  'Ward 1': [17.3850, 78.4867],
  'Ward 2': [17.4000, 78.4500],
  'Ward 3': [17.4200, 78.5000],
  'Ward 4': [17.3500, 78.4700],
};

const SpatialIntelligence = () => {
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHeatmap = () => {
    setLoading(true);
    setError(null);
    api.getHeatmap()
      .then(setHeatmap)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchHeatmap();
  }, []);

  const maxWard = heatmap.length > 0 ? heatmap.reduce((max, h) => (h.count > max.count ? h : max), heatmap[0]) : null;

  return (
    <div className="spatial-page">
      <div className="map-container">
        <MapContainer center={[17.3850, 78.4867] as any} zoom={13} style={{ height: '100%', width: '100%' }}>
          <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
          {heatmap.map(h => (
            <CircleMarker
              key={h.ward}
              center={wardLocations[h.ward] || [17.3850, 78.4867]}
              radius={Math.max(h.count * 5, 8)}
              pathOptions={{ color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.6 }}
            >
              <Popup>
                <div className="popup-content">
                  <h4>{h.ward}</h4>
                  <p>{h.count} active incidents</p>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>

      <div className="gis-controls">
        {error && (
          <div className="gis-panel error-panel">
            <h3><AlertTriangle size={14} /> Error</h3>
            <p>{error}</p>
            <button className="retry-btn" onClick={fetchHeatmap}><RefreshCw size={14} /> Retry</button>
          </div>
        )}
        <div className="gis-panel ai-recommendation">
          <h3><Zap size={14} /> AI Optimization</h3>
          <p className="recommendation-text">
            {loading
              ? 'Analyzing incident density...'
              : maxWard
                ? `Highest incident density detected in ${maxWard.ward} (${maxWard.count} incidents). Recommending dispatch of 2 additional field teams.`
                : 'No heatmap data available. Try refreshing when data is available.'}
          </p>
        </div>
        <div className="gis-panel">
          <h3>Incident Density</h3>
          <div className="legend-item"><div className="color-dot" style={{ background: '#3b82f6' }}></div> <span>High Density</span></div>
          <div className="legend-item"><div className="color-dot" style={{ background: '#60a5fa' }}></div> <span>Medium Density</span></div>
          {heatmap.length > 0 && (
            <div className="legend-item"><div className="color-dot" style={{ background: '#93c5fd' }}></div> <span>Low Density</span></div>
          )}
          {heatmap.length === 0 && !loading && !error && (
            <p className="legend-item">No density data available.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default SpatialIntelligence;
