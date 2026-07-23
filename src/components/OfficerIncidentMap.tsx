import { useEffect, useMemo } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Incident } from '../types';
import './OfficerIncidentMap.css';

interface ComplaintCoordinate {
  id: string;
  latitude: number;
  longitude: number;
  address?: string | null;
}

interface OfficerIncidentMapProps {
  incidents: Incident[];
  complaintCoordinates: ComplaintCoordinate[];
  loading: boolean;
  error: string | null;
  scopeLabel: string;
  scopeWarning: boolean;
}

interface IncidentMapPoint {
  incident: Incident;
  latitude: number;
  longitude: number;
  complaintCount: number;
  address: string | null;
}

const COIMBATORE_BOUNDS: [[number, number], [number, number]] = [
  [10.75, 76.80],
  [11.15, 77.10],
];

const getPriorityColor = (priority?: string): string => {
  switch (priority?.toLowerCase()) {
    case 'critical': return '#ef4444';
    case 'high': return '#f97316';
    case 'medium': return '#eab308';
    case 'low': return '#22c55e';
    default: return '#64748b';
  }
};

const MapViewport = ({ points }: { points: IncidentMapPoint[] }) => {
  const map = useMap();

  useEffect(() => {
    if (!points.length) return;
    const bounds = L.latLngBounds(points.map(point => [point.latitude, point.longitude] as [number, number]));
    map.fitBounds(bounds, { padding: [28, 28], maxZoom: 14 });
  }, [map, points]);

  return null;
};

const OfficerIncidentMap = ({
  incidents,
  complaintCoordinates,
  loading,
  error,
  scopeLabel,
  scopeWarning,
}: OfficerIncidentMapProps) => {
  const points = useMemo(() => {
    const coordinatesByComplaint = new Map(complaintCoordinates.map(coordinate => [coordinate.id, coordinate]));

    return incidents.flatMap<IncidentMapPoint>(incident => {
      const coordinates = (incident.complaints || [])
        .map(complaint => coordinatesByComplaint.get(complaint.id))
        .filter((coordinate): coordinate is ComplaintCoordinate => Boolean(coordinate));

      if (!coordinates.length) return [];

      return [{
        incident,
        latitude: coordinates.reduce((sum, coordinate) => sum + coordinate.latitude, 0) / coordinates.length,
        longitude: coordinates.reduce((sum, coordinate) => sum + coordinate.longitude, 0) / coordinates.length,
        complaintCount: coordinates.length,
        address: coordinates[0].address || null,
      }];
    });
  }, [complaintCoordinates, incidents]);

  return (
    <section className="officer-map-card">
      <div className="officer-map-header">
        <div>
          <p className="officer-map-eyebrow">Officer Assignment View</p>
          <h2>Incidents near you</h2>
          <p className="officer-map-subtitle">Markers use the locations of linked citizen reports.</p>
        </div>
        <div className={`officer-map-scope ${scopeWarning ? 'warning' : ''}`}>
          <span className="officer-map-scope-dot" />
          {scopeLabel}
        </div>
      </div>

      {scopeWarning && (
        <div className="officer-map-warning">
          Your account has no linked ward or zone. Showing all incidents instead of guessing an assignment scope.
        </div>
      )}

      <div className="officer-map-shell">
        {loading ? (
          <div className="officer-map-state">Loading incident locations...</div>
        ) : error ? (
          <div className="officer-map-state error">Incident locations unavailable: {error}</div>
        ) : points.length === 0 ? (
          <div className="officer-map-state">No plotted incidents match the current filters.</div>
        ) : (
          <MapContainer
            center={[11.0168, 76.9558]}
            zoom={13}
            style={{ height: '100%', width: '100%' }}
            zoomControl
            attributionControl={false}
            maxBounds={COIMBATORE_BOUNDS}
            minZoom={11}
            maxZoom={18}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              maxZoom={19}
              attribution="&copy; OpenStreetMap contributors"
            />
            <MapViewport points={points} />
            {points.map(point => (
              <CircleMarker
                key={point.incident.id}
                center={[point.latitude, point.longitude]}
                radius={point.incident.priority_label === 'Critical' ? 9 : 7}
                pathOptions={{
                  fillColor: getPriorityColor(point.incident.priority_label),
                  fillOpacity: 0.85,
                  color: '#fff',
                  weight: 2,
                }}
              >
                <Tooltip direction="top" offset={[0, -8]}>
                  {point.incident.incident_number} · {point.incident.priority_label}
                </Tooltip>
                <Popup>
                  <div className="officer-map-popup">
                    <strong>{point.incident.incident_number}</strong>
                    <span>{point.incident.category} · Ward {point.incident.ward}</span>
                    <span>{point.incident.priority_label} · {point.incident.status}</span>
                    <span>{point.complaintCount} linked report{point.complaintCount === 1 ? '' : 's'}</span>
                    {point.address && <span>{point.address}</span>}
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        )}
      </div>

      <div className="officer-map-footer">
        <span>{points.length} of {incidents.length} filtered incidents plotted</span>
        <span>Incidents without linked coordinates are omitted from the map.</span>
      </div>
    </section>
  );
};

export default OfficerIncidentMap;
