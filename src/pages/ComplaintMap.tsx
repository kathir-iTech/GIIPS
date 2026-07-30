import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { MapPin, Clock, AlertTriangle } from 'lucide-react';
import Header from '../components/Header';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const ComplaintMap = () => {
  const { t } = useTranslation();
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const [markers, setMarkers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getComplaintCoordinates()
      .then(data => {
        if (Array.isArray(data)) setMarkers(data);
        else setMarkers([]);
      })
      .catch(() => setMarkers([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;
    mapInstanceRef.current = L.map(mapRef.current).setView([11.0168, 76.9558], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: 'OpenStreetMap | GIIPS',
      maxZoom: 18,
    }).addTo(mapInstanceRef.current);
    return () => { mapInstanceRef.current?.remove(); mapInstanceRef.current = null; };
  }, []);

  useEffect(() => {
    if (!mapInstanceRef.current || markers.length === 0) return;
    mapInstanceRef.current.eachLayer((layer: any) => { if (layer instanceof L.CircleMarker) layer.remove(); });
    markers.forEach((m: any) => {
      if (!m.latitude || !m.longitude) return;
      L.circleMarker([m.latitude, m.longitude], {
        radius: 6, fillColor: '#ef4444', color: '#991b1b', weight: 1, opacity: 0.8, fillOpacity: 0.6
      }).addTo(mapInstanceRef.current)
        .bindPopup(`<b>${m.predicted_category || t('common.uncategorized')}</b><br/>${t('incidents.wardPrefix', { ward: m.ward })}<br/>${m.days_open ? `${m.days_open}d open` : ''}`);
    });
  }, [markers]);

  return (
    <div className="page-container">
      <Header title={t('complaintMap.title')} subtitle={t('complaintMap.subtitle')} />
      {loading ? (
        <p className="loading-text">{t('common.loading')}</p>
      ) : (
        <div ref={mapRef} style={{ height: '600px', borderRadius: '12px', overflow: 'hidden', border: '1px solid #334155' }} />
      )}
    </div>
  );
};
export default ComplaintMap;
