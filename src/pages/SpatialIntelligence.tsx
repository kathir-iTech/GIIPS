import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { api } from '../services/api';
import { tamilNaduDistricts, districtCentroids } from '../data/tamil-nadu-districts';
import {
  AlertTriangle, RefreshCw, MapPin, Filter, Layers,
  Calendar, AlertOctagon, Activity, Brain, Zap,
  X, Clock,
  ShieldAlert, Map as MapIcon,
  ThermometerSun, Gauge, Users, Target,
  ArrowUpRight, Radio
} from 'lucide-react';
import './SpatialIntelligence.css';

const mapWardToDistrict = (ward: string): string => {
  if (!ward) return 'Unknown';
  const numMatch = ward.match(/\d+/);
  if (numMatch) {
    const num = parseInt(numMatch[0], 10);
    const districtMap: Record<number, string> = {
      1: 'Chennai', 2: 'Kanchipuram', 3: 'Vellore', 4: 'Vellore',
      5: 'Tiruvannamalai', 6: 'Villupuram', 7: 'Cuddalore', 8: 'Cuddalore',
      9: 'Krishnagiri', 10: 'Dharmapuri', 11: 'Salem', 12: 'Namakkal',
      13: 'Erode', 14: 'Tiruppur', 15: 'Coimbatore', 16: 'Perambalur',
      17: 'Ariyalur', 18: 'Karur', 19: 'Tiruchirappalli', 20: 'Thanjavur',
      21: 'Mayiladuthurai', 22: 'Thiruvarur', 23: 'Nagapattinam',
      24: 'Pudukkottai', 25: 'Dindigul', 26: 'Madurai', 27: 'Theni',
      28: 'Sivaganga', 29: 'Virudhunagar', 30: 'Thoothukudi',
      31: 'Tirunelveli', 32: 'Kanyakumari'
    };
    return districtMap[num] || 'Other';
  }
  return ward;
};

const getPriorityColor = (priority: string): string => {
  switch (priority?.toLowerCase()) {
    case 'critical': return '#ef4444';
    case 'high': return '#f97316';
    case 'medium': return '#eab308';
    case 'low': return '#22c55e';
    default: return '#64748b';
  }
};

const TileErrorListener = ({ onError }: { onError: () => void }) => {
  const map = useMap();
  useEffect(() => {
    const handler = () => onError();
    map.on('tileerror', handler);
    return () => { map.off('tileerror', handler); };
  }, [map, onError]);
  return null;
};

const SpatialIntelligence = () => {
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [hotspots, setHotspots] = useState<any[]>([]);
  const [riskData, setRiskData] = useState<any[]>([]);
  const [forecast, setForecast] = useState<any>(null);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [deptWorkload, setDeptWorkload] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null);
  const [hoveredDistrict, setHoveredDistrict] = useState<string | null>(null);
  const [mapKey, setMapKey] = useState(0);
  const [tileError, setTileError] = useState(false);

  const [timelineDays, setTimelineDays] = useState<number>(7);
  const [layers, setLayers] = useState({
    complaints: true,
    incidents: true,
    risk: true,
    prediction: true,
    deptWorkload: true,
  });
  const [filters, setFilters] = useState({
    district: 'all',
    category: 'all',
    priority: 'all',
    date: 'all',
    department: 'all',
  });
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);
  const [selectedIncident, setSelectedIncident] = useState<any | null>(null);
  const [showMobileFilters, setShowMobileFilters] = useState(false);

  const districtData = useMemo(() => {
    const data: Record<string, any> = {};
    heatmap.forEach((h: any) => {
      const district = h.district || (typeof h.ward === 'string' ? mapWardToDistrict(h.ward) : 'Unknown');
      if (!data[district]) {
        data[district] = { count: 0, riskScore: 0, healthScore: 100, categories: {}, criticalCount: 0, incidents: [], totalPopulation: 0 };
      }
      data[district].count += h.count || 0;
      if (h.population) data[district].totalPopulation += h.population;
    });
    incidents.forEach((inc: any) => {
      const district = inc.district || (typeof inc.ward === 'string' ? mapWardToDistrict(inc.ward) : 'Unknown');
      if (!data[district]) {
        data[district] = { count: 0, riskScore: 0, healthScore: 100, categories: {}, criticalCount: 0, incidents: [], totalPopulation: 0 };
      }
      data[district].incidents.push(inc);
      data[district].categories[inc.category] = (data[district].categories[inc.category] || 0) + 1;
      if (inc.priority_label === 'Critical') data[district].criticalCount++;
      if (inc.population) data[district].totalPopulation += inc.population;
    });
    riskData.forEach((r: any) => {
      const district = r.district || r.name || r.ward;
      if (data[district]) {
        data[district].riskScore = r.risk_score ?? r.riskScore ?? data[district].riskScore;
        data[district].healthScore = r.health_score ?? r.healthScore ?? data[district].healthScore;
      }
    });
    Object.keys(data).forEach((d) => {
      if (!data[d].healthScore || data[d].healthScore === 100) {
        data[d].healthScore = Math.max(0, 100 - (data[d].count || 0) * 2);
      }
    });
    return data;
  }, [heatmap, incidents, riskData]);

  const selectedDistrictData = useMemo(() => {
    if (!selectedDistrict) return null;
    return districtData[selectedDistrict] || null;
  }, [districtData, selectedDistrict]);

  const filteredIncidents = useMemo(() => {
    let result = [...incidents];
    if (filters.district !== 'all') result = result.filter((i: any) => (i.district || mapWardToDistrict(i.ward)) === filters.district);
    if (filters.category !== 'all') result = result.filter((i: any) => i.category === filters.category);
    if (filters.priority !== 'all') result = result.filter((i: any) => i.priority_label?.toLowerCase() === filters.priority);
    if (filters.department !== 'all') result = result.filter((i: any) => (i.department || i.category) === filters.department);
    return result;
  }, [incidents, filters]);

  const categories = useMemo(() => {
    const cats = new Set(incidents.map((i: any) => i.category).filter(Boolean));
    return Array.from(cats).sort();
  }, [incidents]);

  const departments = useMemo(() => {
    const depts = new Set(incidents.map((i: any) => i.department).filter(Boolean));
    return Array.from(depts).sort();
  }, [incidents]);

  const districts = useMemo(() => Object.keys(districtData).sort(), [districtData]);

  const totalComplaints = useMemo(() => heatmap.reduce((sum, h: any) => sum + (h.count || 0), 0), [heatmap]);
  const totalIncidents = useMemo(() => incidents.length, [incidents]);
  const criticalCount = useMemo(() => incidents.filter((i: any) => i.priority_label === 'Critical').length, [incidents]);
  const avgRisk = useMemo(() => {
    const risks = Object.values(districtData).map((d: any) => d.riskScore).filter((r: any) => r > 0);
    return risks.length > 0 ? Math.round(risks.reduce((a: number, b: number) => a + b, 0) / risks.length) : 0;
  }, [districtData]);

  const forecastDistricts = useMemo(() => {
    if (!forecast) return new Set<string>();
    const dists = new Set<string>();
    if (Array.isArray(forecast)) {
      forecast.forEach((f: any) => {
        if (f.district && (f.expected_to_worsen || f.trend === 'worsening')) dists.add(f.district);
      });
    }
    return dists;
  }, [forecast]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.allSettled([
      api.getHeatmap(),
      api.getHotspots(),
      api.getRiskAnalysis(),
      api.getForecast(timelineDays),
      api.getIncidents(),
    ]).then((results: any) => {
      if (cancelled) return;
      const errors: string[] = [];
      if (results[0].status === 'fulfilled') setHeatmap(Array.isArray(results[0].value) ? results[0].value : []);
      else errors.push('heatmap');
      if (results[1].status === 'fulfilled') setHotspots(Array.isArray(results[1].value) ? results[1].value : []);
      else errors.push('hotspots');
      if (results[2].status === 'fulfilled') setRiskData(Array.isArray(results[2].value) ? results[2].value : []);
      else errors.push('risk');
      if (results[3].status === 'fulfilled') setForecast(results[3].value || null);
      else errors.push('forecast');
      if (results[4].status === 'fulfilled') setIncidents(Array.isArray(results[4].value) ? results[4].value : []);
      else errors.push('incidents');
      if (errors.length > 0) setError(`Some feeds offline: ${errors.join(', ')}. Showing best available data.`);
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [timelineDays]);

  const handleDistrictClick = useCallback((district: string) => {
    setSelectedDistrict((prev) => (prev === district ? null : district));
  }, []);

  const handleLayerToggle = useCallback((layer: keyof typeof layers) => {
    setLayers((prev) => ({ ...prev, [layer]: !prev[layer] }));
  }, []);

  const handleFilterChange = useCallback((key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSimulate = useCallback(async (teams: number) => {
    setSimulating(true);
    setSimResult(null);
    try {
      const result = await api.simulateResources(teams);
      setSimResult(result);
    } catch (err) {
      console.error('Simulation failed:', err);
      setSimResult({ error: 'Simulation failed. Please try again.' });
    } finally {
      setSimulating(false);
    }
  }, []);

  const handleRetry = useCallback(() => {
    setError(null);
    setLoading(true);
    Promise.allSettled([
      api.getHeatmap(),
      api.getHotspots(),
      api.getRiskAnalysis(),
      api.getForecast(timelineDays),
      api.getIncidents(),
    ]).then((results: any) => {
      if (results[0].status === 'fulfilled') setHeatmap(Array.isArray(results[0].value) ? results[0].value : []);
      if (results[1].status === 'fulfilled') setHotspots(Array.isArray(results[1].value) ? results[1].value : []);
      if (results[2].status === 'fulfilled') setRiskData(Array.isArray(results[2].value) ? results[2].value : []);
      if (results[3].status === 'fulfilled') setForecast(results[3].value || null);
      if (results[4].status === 'fulfilled') setIncidents(Array.isArray(results[4].value) ? results[4].value : []);
    }).finally(() => setLoading(false));
  }, [timelineDays]);

  const handleIncidentClick = useCallback((incident: any) => {
    setSelectedIncident(incident);
  }, []);

  const getDistrictColor = useCallback((districtName: string): string => {
    const data = districtData[districtName];
    if (!data) return 'transparent';
    const count = data.count || 0;
    if (count === 0) return 'transparent';
    if (count <= 5) return '#22c55e';
    if (count <= 15) return '#eab308';
    if (count <= 30) return '#f97316';
    return '#ef4444';
  }, [districtData]);

  const generateAIRecommendation = useCallback((district: string): string => {
    const data = districtData[district];
    if (!data) return 'No data available for this district.';
    const recommendations: string[] = [];
    if ((data.riskScore || 0) > 70) recommendations.push('Immediate intervention recommended due to high risk score.');
    if (data.criticalCount > 3) recommendations.push(`Deploy ${Math.ceil(data.criticalCount / 2)} additional field teams for ${data.criticalCount} critical incidents.`);
    if ((data.healthScore || 100) < 50) recommendations.push('Comprehensive infrastructure review needed — health score below threshold.');
    if (recommendations.length === 0) recommendations.push('Monitor situation. Current indicators are within acceptable parameters.');
    return recommendations.join(' ');
  }, [districtData]);

  const getTopCategory = useCallback((district: string): string => {
    const data = districtData[district];
    if (!data || !data.categories) return 'N/A';
    const entries = Object.entries(data.categories);
    if (entries.length === 0) return 'N/A';
    entries.sort((a: any, b: any) => (b[1] as number) - (a[1] as number));
    return entries[0][0];
  }, [districtData]);

  if (loading && heatmap.length === 0 && incidents.length === 0) {
    return (
      <div className="command-center">
        <header className="command-header">
          <div className="header-brand">
            <div className="header-logo"><ShieldAlert size={22} /></div>
            <div>
              <h1>Spatial Intelligence Command Center</h1>
              <p>AI-Powered Governance GIS — Tamil Nadu State Overview</p>
            </div>
          </div>
          <div className="header-status">
            <span className="status-dot loading" />
            <span>Loading intelligence feeds...</span>
          </div>
        </header>
        <div className="loading-overlay">
          <div className="loading-spinner" />
          <p>Initializing command center...</p>
          <div className="loading-bars">
            {['Fetching heatmap data', 'Loading hotspots', 'Syncing risk analysis', 'Loading forecast model', 'Retrieving incidents'].map((text, i) => (
              <div key={i} className="loading-bar-item">
                <div className="loading-bar-track">
                  <div className="loading-bar-fill" style={{ animationDelay: `${i * 0.3}s` }} />
                </div>
                <span>{text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error && heatmap.length === 0 && incidents.length === 0) {
    return (
      <div className="command-center">
        <header className="command-header">
          <div className="header-brand">
            <div className="header-logo"><ShieldAlert size={22} /></div>
            <div>
              <h1>Spatial Intelligence Command Center</h1>
              <p>AI-Powered Governance GIS — Tamil Nadu State Overview</p>
            </div>
          </div>
        </header>
        <div className="error-overlay">
          <AlertTriangle size={48} />
          <h2>Intelligence Feeds Unavailable</h2>
          <p>{error}</p>
          <button className="retry-btn" onClick={handleRetry}>
            <RefreshCw size={16} /> Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (!loading && heatmap.length === 0 && incidents.length === 0) {
    return (
      <div className="command-center">
        <header className="command-header">
          <div className="header-brand">
            <div className="header-logo"><ShieldAlert size={22} /></div>
            <div>
              <h1>Spatial Intelligence Command Center</h1>
              <p>AI-Powered Governance GIS — Tamil Nadu State Overview</p>
            </div>
          </div>
        </header>
        <div className="empty-overlay">
          <MapIcon size={48} />
          <h2>No Intelligence Data Available</h2>
          <p>There are currently no incidents or complaints to display on the map.</p>
          <button className="retry-btn" onClick={handleRetry}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="command-center">
      <header className="command-header">
        <div className="header-brand">
          <div className="header-logo"><ShieldAlert size={22} /></div>
          <div>
            <h1>Spatial Intelligence Command Center</h1>
            <p>AI-Powered Governance GIS — Tamil Nadu State Overview</p>
          </div>
        </div>
        <div className="header-kpis">
          <div className="kpi-mini">
            <span className="kpi-mini-value">{totalComplaints.toLocaleString()}</span>
            <span className="kpi-mini-label">Complaints</span>
          </div>
          <div className="kpi-mini">
            <span className="kpi-mini-value">{totalIncidents}</span>
            <span className="kpi-mini-label">Incidents</span>
          </div>
          <div className="kpi-mini critical">
            <span className="kpi-mini-value">{criticalCount}</span>
            <span className="kpi-mini-label">Critical</span>
          </div>
          <div className="kpi-mini">
            <span className="kpi-mini-value">{avgRisk}%</span>
            <span className="kpi-mini-label">Avg Risk</span>
          </div>
        </div>
        <div className="header-actions">
          <button className="mobile-filter-toggle" onClick={() => setShowMobileFilters(!showMobileFilters)}>
            <Filter size={18} />
          </button>
          <button className="refresh-btn" onClick={handleRetry} title="Refresh data">
            <RefreshCw size={18} />
          </button>
          <div className="header-datetime">
            <Clock size={14} />
            <span>{new Date().toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</span>
          </div>
        </div>
      </header>

      <div className="command-body">
        <aside className={`command-left-panel ${showMobileFilters ? 'open' : ''}`}>
          <div className="panel-section">
            <h3><Layers size={14} /> Map Layers</h3>
            <div className="layer-toggles">
              {[
                { key: 'complaints', label: 'Complaints', icon: AlertTriangle },
                { key: 'incidents', label: 'Incidents', icon: AlertOctagon },
                { key: 'risk', label: 'Risk Analysis', icon: ThermometerSun },
                { key: 'prediction', label: 'AI Prediction', icon: Brain },
                { key: 'deptWorkload', label: 'Dept Workload', icon: Users },
              ].map(({ key, label, icon: Icon }) => (
                <label key={key} className={`layer-toggle ${layers[key as keyof typeof layers] ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={layers[key as keyof typeof layers]}
                    onChange={() => handleLayerToggle(key as keyof typeof layers)}
                  />
                  <Icon size={14} />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="panel-section">
            <h3><Filter size={14} /> Smart Filters</h3>
            <div className="filter-grid">
              <div className="filter-field">
                <label>District</label>
                <select value={filters.district} onChange={(e) => handleFilterChange('district', e.target.value)}>
                  <option value="all">All Districts</option>
                  {districts.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div className="filter-field">
                <label>Category</label>
                <select value={filters.category} onChange={(e) => handleFilterChange('category', e.target.value)}>
                  <option value="all">All Categories</option>
                  {categories.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div className="filter-field">
                <label>Priority</label>
                <select value={filters.priority} onChange={(e) => handleFilterChange('priority', e.target.value)}>
                  <option value="all">All Priorities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
              <div className="filter-field">
                <label>Department</label>
                <select value={filters.department} onChange={(e) => handleFilterChange('department', e.target.value)}>
                  <option value="all">All Departments</option>
                  {departments.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="panel-section">
            <h3><Calendar size={14} /> Forecast Timeline</h3>
            <div className="timeline-buttons">
              {[7, 15, 30].map((days) => (
                <button
                  key={days}
                  className={`timeline-btn ${timelineDays === days ? 'active' : ''}`}
                  onClick={() => setTimelineDays(days)}
                >
                  {days} Days
                </button>
              ))}
            </div>
            {forecast && (
              <div className="forecast-summary">
                <p><Activity size={12} /> Forecast loaded for {timelineDays} days</p>
              </div>
            )}
          </div>

          <div className="panel-section">
            <h3><MapPin size={14} /> Heatmap Legend</h3>
            <div className="legend-items">
              {[
                { color: '#22c55e', label: 'Low (0-5)' },
                { color: '#eab308', label: 'Medium (6-15)' },
                { color: '#f97316', label: 'High (16-30)' },
                { color: '#ef4444', label: 'Critical (30+)' },
              ].map(({ color, label }) => (
                <div key={label} className="legend-item">
                  <div className="legend-dot" style={{ background: color }} />
                  <span>{label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="panel-section">
            <h3><Radio size={14} /> Hotspots</h3>
            <div className="legend-items">
              <div className="legend-item">
                <div className="legend-dot hotspot" />
                <span>Active Hotspot</span>
              </div>
            </div>
          </div>
        </aside>

        <div className="command-map">
          <MapContainer
            key={mapKey}
            center={[10.5, 78.5] as any}
            zoom={7}
            style={{ height: '100%', width: '100%' }}
            zoomControl={false}
            attributionControl={false}
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              maxZoom={19}
            />
            <TileErrorListener onError={() => setTileError(true)} />

            {layers.complaints && (
              <GeoJSON
                data={tamilNaduDistricts as any}
                style={(feature: any) => {
                  const districtName = feature.properties?.name || feature.properties?.district;
                  const isForecast = forecastDistricts.has(districtName);
                  const baseColor = getDistrictColor(districtName);
                  return {
                    fillColor: isForecast ? '#f97316' : baseColor,
                    weight: selectedDistrict === districtName ? 3 : hoveredDistrict === districtName ? 2 : 1,
                    opacity: 0.9,
                    color: isForecast ? '#fbbf24' : selectedDistrict === districtName ? '#3b82f6' : 'rgba(255,255,255,0.3)',
                    dashArray: isForecast ? '5, 5' : undefined,
                    fillOpacity: isForecast ? 0.3 : baseColor === 'transparent' ? 0.05 : 0.2,
                  };
                }}
                onEachFeature={(feature: any, layer: any) => {
                  const districtName = feature.properties?.name || feature.properties?.district;
                  layer.on({
                    click: () => handleDistrictClick(districtName),
                    mouseover: () => setHoveredDistrict(districtName),
                    mouseout: () => setHoveredDistrict(null),
                  });
                  if (districtData[districtName]) {
                    layer.bindTooltip(
                      `<div style="padding:8px;background:#0f172a;border:1px solid rgba(148,163,184,0.2);border-radius:8px;color:#f8fafc;font-size:12px;min-width:140px;">
                        <strong style="font-size:13px;">${districtName}</strong><br/>
                        <span style="color:#94a3b8;">Complaints:</span> <strong>${districtData[districtName].count || 0}</strong><br/>
                        <span style="color:#94a3b8;">Critical:</span> <strong style="color:#ef4444;">${districtData[districtName].criticalCount || 0}</strong>
                      </div>`,
                      { sticky: true, className: 'district-tooltip' }
                    );
                  }
                }}
              />
            )}

            {layers.risk && riskData.length > 0 && (
              <GeoJSON
                key="risk-layer"
                data={{
                  type: 'FeatureCollection',
                  features: riskData.map((r: any) => {
                    const districtName = r.district || r.name || r.ward;
                    const geoFeature = tamilNaduDistricts.features.find((f: any) => f.properties.name === districtName);
                    return {
                      type: 'Feature',
                      properties: { name: districtName, riskScore: r.risk_score ?? r.riskScore ?? 0 },
                      geometry: geoFeature?.geometry || { type: 'Polygon', coordinates: [[[0, 0], [0, 0], [0, 0]]] },
                    };
                  }),
                } as any}
                style={(feature: any) => {
                  const score = feature.properties?.riskScore || 0;
                  return {
                    fillColor: score > 70 ? '#ef4444' : score > 40 ? '#eab308' : '#22c55e',
                    weight: 1,
                    opacity: 0.6,
                    color: 'transparent',
                    fillOpacity: 0.15,
                  };
                }}
              />
            )}

            {layers.incidents && hotspots.map((hotspot: any, idx: number) => {
              const lat = hotspot.lat || hotspot.latitude || hotspot.y;
              const lng = hotspot.lng || hotspot.longitude || hotspot.x;
              if (!lat || !lng) return null;
              return (
                <CircleMarker
                  key={`hotspot-${idx}`}
                  center={[lat, lng] as any}
                  radius={Math.max((hotspot.count || hotspot.intensity || 1) * 3, 6)}
                  pathOptions={{
                    fillColor: '#ef4444',
                    fillOpacity: 0.7,
                    color: '#fff',
                    weight: 2,
                  }}
                >
                  <Popup>
                    <div className="incident-popup">
                      <h4>Hotspot #{idx + 1}</h4>
                      <p><strong>Intensity:</strong> {hotspot.count || hotspot.intensity || 'N/A'}</p>
                      {hotspot.category && <p><strong>Category:</strong> {hotspot.category}</p>}
                      {hotspot.ward && <p><strong>Ward:</strong> {hotspot.ward}</p>}
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}

            {layers.incidents && filteredIncidents.map((inc: any) => {
              const districtName = inc.district || mapWardToDistrict(inc.ward);
              const centroid = districtCentroids[districtName];
              if (!centroid) return null;
              return (
                <CircleMarker
                  key={`inc-${inc.id}`}
                  center={[centroid[0], centroid[1]] as any}
                  radius={4}
                  pathOptions={{
                    fillColor: getPriorityColor(inc.priority_label),
                    fillOpacity: 0.85,
                    color: '#fff',
                    weight: 1.5,
                  }}
                  eventHandlers={{
                    click: () => handleIncidentClick(inc),
                  }}
                >
                  <Tooltip direction="top" offset={[0, -8]} className="incident-tooltip">
                    <strong>{inc.incident_number}</strong> — {inc.priority_label}
                  </Tooltip>
                </CircleMarker>
              );
            })}
          </MapContainer>

          <div className="map-overlay-info">
            <span className="map-source">Base: CARTO Dark Matter</span>
            {error && <span className="map-warning"><AlertTriangle size={12} /> Partial data</span>}
            {tileError && <span className="map-warning"><AlertTriangle size={12} /> Tile load error</span>}
          </div>
        </div>

        {selectedDistrict && selectedDistrictData && (
          <aside className="command-right-panel">
            <div className="panel-header">
              <h3>{selectedDistrict}</h3>
              <button className="close-panel" onClick={() => setSelectedDistrict(null)}>
                <X size={18} />
              </button>
            </div>
            <div className="panel-content">
              <div className="detail-grid">
                <div className="detail-card">
                  <span className="detail-label">Complaints</span>
                  <span className="detail-value">{selectedDistrictData.count || 0}</span>
                </div>
                <div className="detail-card">
                  <span className="detail-label">Risk Score</span>
                  <span className={`detail-value ${(selectedDistrictData.riskScore || 0) > 70 ? 'critical' : (selectedDistrictData.riskScore || 0) > 40 ? 'warning' : 'good'}`}>
                    {selectedDistrictData.riskScore || 0}%
                  </span>
                </div>
                <div className="detail-card">
                  <span className="detail-label">Health Score</span>
                  <span className={`detail-value ${(selectedDistrictData.healthScore || 100) < 50 ? 'critical' : (selectedDistrictData.healthScore || 100) < 70 ? 'warning' : 'good'}`}>
                    {selectedDistrictData.healthScore || 100}%
                  </span>
                </div>
                <div className="detail-card">
                  <span className="detail-label">Critical Incidents</span>
                  <span className="detail-value critical">{selectedDistrictData.criticalCount || 0}</span>
                </div>
              </div>

              <div className="detail-section">
                <h4><Target size={14} /> Top Category</h4>
                <p className="detail-text">{getTopCategory(selectedDistrict)}</p>
              </div>

              <div className="detail-section">
                <h4><Brain size={14} /> AI Recommendation</h4>
                <p className="detail-text recommendation">{generateAIRecommendation(selectedDistrict)}</p>
              </div>

              <div className="detail-section">
                <h4><Zap size={14} /> Resource Simulation</h4>
                <div className="sim-controls">
                  <button className="sim-btn" onClick={() => handleSimulate(2)} disabled={simulating}>
                    {simulating ? <RefreshCw size={14} className="spin" /> : <Users size={14} />} +2 Teams
                  </button>
                  <button className="sim-btn" onClick={() => handleSimulate(5)} disabled={simulating}>
                    {simulating ? <RefreshCw size={14} className="spin" /> : <Users size={14} />} +5 Teams
                  </button>
                </div>
                {simResult && (
                  <div className="sim-result">
                    <p><strong>Simulation Result:</strong></p>
                    <pre>{JSON.stringify(simResult, null, 2)}</pre>
                  </div>
                )}
              </div>

              <div className="detail-section">
                <h4><AlertOctagon size={14} /> Incidents in District</h4>
                <div className="incident-list">
                  {(selectedDistrictData.incidents || []).slice(0, 5).map((inc: any) => (
                    <div key={inc.id} className="incident-item" onClick={() => handleIncidentClick(inc)}>
                      <div className="incident-item-header">
                        <span className="incident-id">{inc.incident_number}</span>
                        <span className={`priority-badge ${inc.priority_label?.toLowerCase() || 'medium'}`}>
                          {inc.priority_label}
                        </span>
                      </div>
                      <p className="incident-summary">{inc.summary || inc.category}</p>
                      <span className="incident-meta"><Clock size={10} /> {inc.days_open || 0}d open</span>
                    </div>
                  ))}
                  {(selectedDistrictData.incidents || []).length === 0 && (
                    <p className="no-data">No incidents in this district.</p>
                  )}
                </div>
              </div>
            </div>
          </aside>
        )}
      </div>

      <footer className="command-footer">
        <div className="footer-left">
          <span className="footer-brand">GIIPS Spatial Intelligence v2.1</span>
          <span className="footer-status">
            <span className="status-dot" /> System Operational
          </span>
        </div>
        <div className="footer-right">
          <span>Data refreshed: {new Date().toLocaleString('en-IN')}</span>
          <span className="footer-badge">Tamil Nadu State GIS</span>
        </div>
      </footer>

      {selectedIncident && (
        <div className="floating-incident-popup">
          <div className="popup-header">
            <h4>{selectedIncident.incident_number}</h4>
            <button className="close-popup" onClick={() => setSelectedIncident(null)}>
              <X size={16} />
            </button>
          </div>
          <div className="popup-body">
            <div className="popup-row">
              <span className="popup-label">Category</span>
              <span className="popup-value">{selectedIncident.category || 'N/A'}</span>
            </div>
            <div className="popup-row">
              <span className="popup-label">Priority</span>
              <span className={`popup-value priority-${selectedIncident.priority_label?.toLowerCase() || 'medium'}`}>
                {selectedIncident.priority_label || 'N/A'}
              </span>
            </div>
            <div className="popup-row">
              <span className="popup-label">Age</span>
              <span className="popup-value">{selectedIncident.days_open || 0} days</span>
            </div>
            <div className="popup-row">
              <span className="popup-label">Affected Population</span>
              <span className="popup-value">{(selectedIncident.population || selectedIncident.cluster_size || 0).toLocaleString()}</span>
            </div>
            <div className="popup-row">
              <span className="popup-label">Recommended Action</span>
              <span className="popup-value">{selectedIncident.recommended_action || 'Pending review'}</span>
            </div>
          </div>
          <div className="popup-footer">
            <button className="open-details-btn" onClick={() => { window.location.href = '/incident-feed'; }}>
              Open Details <ArrowUpRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SpatialIntelligence;
