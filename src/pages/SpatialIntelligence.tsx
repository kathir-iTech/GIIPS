import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { api } from '../services/api';
import { Zap, AlertTriangle } from 'lucide-react';
import './SpatialIntelligence.css';

// Mock locations for wards based on typical city layouts
const wardLocations: Record<string, [number, number]> = {
  'Ward 1': [17.3850, 78.4867],
  'Ward 2': [17.4000, 78.4500],
  'Ward 3': [17.4200, 78.5000],
  'Ward 4': [17.3500, 78.4700],
};

const SpatialIntelligence = () => {
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getHeatmap().then(setHeatmap).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Initializing GIS Engine...</div>;

  return (
    <div className="spatial-page">
      <div className="map-container">
        <MapContainer center={[17.3850, 78.4867] as any} zoom={13} style={{ height: '100%', width: '100%' }}>
          <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
          {heatmap.map(h => (
            <CircleMarker key={h.ward} center={wardLocations[h.ward] || [17.3850, 78.4867]} radius={h.count * 5} pathOptions={{ color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.6 }}>
              <Popup><div className="popup-content"><h4>{h.ward}</h4><p>{h.count} active incidents</p></div></Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>

      <div className="gis-controls">
        <div className="gis-panel ai-recommendation">
          <h3><Zap size={14} /> AI Optimization</h3>
          <p className="recommendation-text">High incident density detected in Ward 1. Recommending dispatch of 2 additional field teams.</p>
        </div>
        <div className="gis-panel">
          <h3>Incident Density</h3>
          <div className="legend-item"><div className="color-dot" style={{background: '#3b82f6'}}></div> <span>High Density</span></div>
          <div className="legend-item"><div className="color-dot" style={{background: '#60a5fa'}}></div> <span>Medium Density</span></div>
        </div>
      </div>
    </div>
  );
};
export default SpatialIntelligence;
