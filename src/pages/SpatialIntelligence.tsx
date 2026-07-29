import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, Tooltip, useMap, Circle } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import { api } from '../services/api';
import { tamilNaduDistricts, districtCentroids } from '../data/tamil-nadu-districts';
import { DEPARTMENT_NAMES, getDeptI18nKey } from '../data/departments';
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

const COIMBATORE_BOUNDS: [[number, number], [number, number]] = [
  [10.75, 76.80],
  [11.15, 77.10],
];

const ComplaintClusterLayer = ({ pins, visible }: { pins: any[]; visible: boolean }) => {
  const { t } = useTranslation();
  const map = useMap();
  const mcgRef = useRef<L.MarkerClusterGroup | null>(null);

  useEffect(() => {
    if (!mcgRef.current) {
      mcgRef.current = L.markerClusterGroup({
        chunkedLoading: true,
        maxClusterRadius: 60,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        disableClusteringAtZoom: 16,
      });
    }

    const mcg = mcgRef.current;

    if (!visible) {
      if (map.hasLayer(mcg)) map.removeLayer(mcg);
      return;
    }

    if (!map.hasLayer(mcg)) map.addLayer(mcg);

    mcg.clearLayers();

    const markers = pins
      .filter(pin => pin.latitude != null && pin.longitude != null)
      .map(pin => {
        const marker = L.circleMarker([pin.latitude, pin.longitude], {
          radius: 6,
          fillColor: getPriorityColor(pin.priority),
          fillOpacity: 0.7,
          color: '#fff',
          weight: 2,
        });
        const html = `
          <div style="max-width:220px;font-size:12px;line-height:1.4;color:#f8fafc;">
            <strong>${pin.title || t('spatialIntelligence.pinFallback')}</strong><br/>
            <span style="color:#94a3b8;">${pin.address || ''}</span>
            ${pin.priority ? `<br/><span style="color:${getPriorityColor(pin.priority)}">${pin.priority}</span>` : ''}
          </div>`;
        marker.bindTooltip(html, { direction: 'top', offset: [0, -8], className: 'complaint-pin-tooltip' });
        return marker;
      });

    mcg.addLayers(markers);

    return () => {
      if (mcgRef.current && map.hasLayer(mcgRef.current)) {
        map.removeLayer(mcgRef.current);
      }
    };
  }, [map, pins, visible]);

  return null;
};

const SpatialIntelligence = () => {
  const { t, i18n } = useTranslation();
  const dateLocale = i18n.language === 'ta' ? 'ta-IN' : 'en-IN';
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [hotspots, setHotspots] = useState<any[]>([]);
  const [riskData, setRiskData] = useState<any[]>([]);
  const [forecast, setForecast] = useState<any>(null);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [complaintPins, setComplaintPins] = useState<any[]>([]);
  const [deptWorkload, setDeptWorkload] = useState<any[]>([]);
  const [geofences, setGeofences] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null);
  const [hoveredDistrict, setHoveredDistrict] = useState<string | null>(null);
  const [mapKey, setMapKey] = useState(0);


  const [timelineDays, setTimelineDays] = useState<number>(7);
  const [layers, setLayers] = useState({
    complaints: true,
    incidents: true,
    complaintPins: true,
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
  const [showGeoClusters, setShowGeoClusters] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareData, setCompareData] = useState<any>(null);

  const openCompare = useCallback(async () => {
    try {
      const [current, historical] = await Promise.all([
        api.getHeatmap(),
        api.getPublicStats ? api.getPublicStats() : Promise.resolve(null),
      ]);
      setCompareData({ current, historical });
      setCompareOpen(true);
    } catch {
      setCompareData(null);
      setCompareOpen(true);
    }
  }, []);

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

  const departments = useMemo(() => DEPARTMENT_NAMES, []);

  const districts = useMemo(() => Object.keys(districtData).sort(), [districtData]);

  const totalComplaints = useMemo(() => heatmap.reduce((sum, h: any) => sum + (h.count || 0), 0), [heatmap]);
  const totalIncidents = useMemo(() => incidents.length, [incidents]);
  const criticalCount = useMemo(() => incidents.filter((i: any) => i.priority_label === 'Critical').length, [incidents]);
  const avgRisk = useMemo(() => {
    const risks = Object.values(districtData).map((d: any) => d.riskScore).filter((r: any) => r > 0);
    return risks.length > 0 ? Math.round(risks.reduce((a: number, b: number) => a + b, 0) / risks.length) : 0;
  }, [districtData]);

  const geoClusters = useMemo(() => {
    const pins = complaintPins;
    if (!pins.length) return [];
    const assigned = new Set<number>();
    const clusters: any[] = [];
    pins.forEach((p: any, i: number) => {
      if (assigned.has(i)) return;
      const group = [p];
      assigned.add(i);
      pins.forEach((q: any, j: number) => {
        if (assigned.has(j)) return;
        const dx = (p.latitude || 0) - (q.latitude || 0);
        const dy = (p.longitude || 0) - (q.longitude || 0);
        if (Math.sqrt(dx*dx + dy*dy) < 0.005) {
          group.push(q);
          assigned.add(j);
        }
      });
      if (group.length >= 2) {
        const cats = group.map(g => g.category || 'Unknown');
        const dominantCat = cats.sort((a,b) => cats.filter(v => v===a).length - cats.filter(v => v===b).length).pop();
        const lat = group.reduce((s: number,g: any) => s + (g.latitude||0), 0) / group.length;
        const lng = group.reduce((s: number,g: any) => s + (g.longitude||0), 0) / group.length;
        clusters.push({ center: [lat, lng], count: group.length, category: dominantCat, incidents: group });
      }
    });
    return clusters;
  }, [complaintPins]);

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
      api.getIncidents(undefined, 2000),
      api.getComplaintCoordinates(),
      api.getGeofences(),
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
      if (results[5].status === 'fulfilled') setComplaintPins(Array.isArray(results[5].value) ? results[5].value : []);
      if (results[6].status === 'fulfilled') setGeofences(Array.isArray(results[6].value) ? results[6].value : []);
      if (errors.length > 0) setError(t('spatialIntelligence.feedsOffline', { feeds: errors.join(', ') }));
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
      setSimResult({ error: t('spatialIntelligence.simulationFailed') });
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
      api.getIncidents(undefined, 2000),
      api.getComplaintCoordinates(),
    ]).then((results: any) => {
      if (results[0].status === 'fulfilled') setHeatmap(Array.isArray(results[0].value) ? results[0].value : []);
      if (results[1].status === 'fulfilled') setHotspots(Array.isArray(results[1].value) ? results[1].value : []);
      if (results[2].status === 'fulfilled') setRiskData(Array.isArray(results[2].value) ? results[2].value : []);
      if (results[3].status === 'fulfilled') setForecast(results[3].value || null);
      if (results[4].status === 'fulfilled') setIncidents(Array.isArray(results[4].value) ? results[4].value : []);
      if (results[5].status === 'fulfilled') setComplaintPins(Array.isArray(results[5].value) ? results[5].value : []);
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
    if (!data) return t('spatialIntelligence.noDistrictData');
    const recommendations: string[] = [];
    if ((data.riskScore || 0) > 70) recommendations.push(t('spatialIntelligence.aiRecHighRisk'));
    if (data.criticalCount > 3) recommendations.push(t('spatialIntelligence.aiRecDeployTeams', { teams: Math.ceil(data.criticalCount / 2), count: data.criticalCount }));
    if ((data.healthScore || 100) < 50) recommendations.push(t('spatialIntelligence.aiRecHealthReview'));
    if (recommendations.length === 0) recommendations.push(t('spatialIntelligence.aiRecMonitor'));
    return recommendations.join(' ');
  }, [districtData]);

  const getTopCategory = useCallback((district: string): string => {
    const data = districtData[district];
    if (!data || !data.categories) return t('common.na');
    const entries = Object.entries(data.categories);
    if (entries.length === 0) return t('common.na');
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
              <h1>{t('spatialIntelligence.header.title')}</h1>
              <p>{t('spatialIntelligence.header.subtitle')}</p>
            </div>
          </div>
          <div className="header-status">
            <span className="status-dot loading" />
            <span>{t('spatialIntelligence.loading.feeds')}</span>
          </div>
        </header>
        <div className="loading-overlay">
          <div className="loading-spinner" />
          <p>{t('spatialIntelligence.loading.initializing')}</p>
          <div className="loading-bars">
            {[t('spatialIntelligence.loading.heatmap'), t('spatialIntelligence.loading.hotspots'), t('spatialIntelligence.loading.riskAnalysis'), t('spatialIntelligence.loading.forecast'), t('spatialIntelligence.loading.incidents')].map((text, i) => (
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
              <h1>{t('spatialIntelligence.header.title')}</h1>
              <p>{t('spatialIntelligence.header.subtitle')}</p>
            </div>
          </div>
        </header>
        <div className="error-overlay">
          <AlertTriangle size={48} />
          <h2>{t('spatialIntelligence.error.title')}</h2>
          <p>{error}</p>
          <button className="retry-btn" onClick={handleRetry}>
            <RefreshCw size={16} /> {t('spatialIntelligence.error.retry')}
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
              <h1>{t('spatialIntelligence.header.title')}</h1>
              <p>{t('spatialIntelligence.header.subtitle')}</p>
            </div>
          </div>
        </header>
        <div className="empty-overlay">
          <MapIcon size={48} />
          <h2>{t('spatialIntelligence.empty.title')}</h2>
          <p>{t('spatialIntelligence.empty.body')}</p>
          <button className="retry-btn" onClick={handleRetry}>
            <RefreshCw size={16} /> {t('spatialIntelligence.empty.refresh')}
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
            <h1>{t('spatialIntelligence.header.title')}</h1>
            <p>{t('spatialIntelligence.header.subtitle')}</p>
          </div>
        </div>
        <div className="header-kpis">
          <div className="kpi-mini">
            <span className="kpi-mini-value">{totalComplaints.toLocaleString()}</span>
            <span className="kpi-mini-label">{t('spatialIntelligence.kpi.complaints')}</span>
          </div>
          <div className="kpi-mini">
            <span className="kpi-mini-value">{totalIncidents}</span>
            <span className="kpi-mini-label">{t('spatialIntelligence.kpi.incidents')}</span>
          </div>
          <div className="kpi-mini critical">
            <span className="kpi-mini-value">{criticalCount}</span>
            <span className="kpi-mini-label">{t('spatialIntelligence.kpi.critical')}</span>
          </div>
          <div className="kpi-mini">
            <span className="kpi-mini-value">{avgRisk}%</span>
            <span className="kpi-mini-label">{t('spatialIntelligence.kpi.avgRisk')}</span>
          </div>
        </div>
        <div className="header-actions">
          <button className="mobile-filter-toggle" onClick={() => setShowMobileFilters(!showMobileFilters)}>
            <Filter size={18} />
          </button>
          <button className="refresh-btn" onClick={handleRetry} title={t('common.tooltip.refresh')}>
            <RefreshCw size={18} />
          </button>
          <button className="compare-btn" onClick={openCompare} title={t('spatialIntelligence.compareButton')}>
            <Gauge size={16} />
          </button>
          <div className="header-datetime">
            <Clock size={14} />
            <span>{new Date().toLocaleString(dateLocale, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</span>
          </div>
        </div>
      </header>

      <div className="command-body">
        <aside className={`command-left-panel ${showMobileFilters ? 'open' : ''}`}>
          <div className="panel-section">
            <h3><Layers size={14} /> {t('spatialIntelligence.sidebar.mapLayers')}</h3>
            <div className="layer-toggles">
              {[
                { key: 'complaints', label: t('spatialIntelligence.layer.complaints'), icon: AlertTriangle },
                { key: 'incidents', label: t('spatialIntelligence.layer.incidents'), icon: AlertOctagon },
                { key: 'complaintPins', label: t('spatialIntelligence.layer.citizenPins'), icon: MapPin },
                { key: 'risk', label: t('spatialIntelligence.layer.risk'), icon: ThermometerSun },
                { key: 'prediction', label: t('spatialIntelligence.layer.prediction'), icon: Brain },
                { key: 'deptWorkload', label: t('spatialIntelligence.layer.deptWorkload'), icon: Users },
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
              <button className={`layer-toggle ${showGeoClusters ? 'active' : ''}`} onClick={() => setShowGeoClusters(!showGeoClusters)} style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', cursor: 'pointer', padding: '8px 10px', borderRadius: 8, background: showGeoClusters ? 'rgba(59, 130, 246, 0.12)' : 'rgba(30, 41, 59, 0.4)', border: showGeoClusters ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid rgba(148, 163, 184, 0.08)', color: showGeoClusters ? '#3b82f6' : '#cbd5e1', fontSize: 12, fontFamily: 'inherit' }}>
                <Radio size={14} /> {t('spatialIntelligence.clustersToggle')}
              </button>
            </div>
          </div>

          <div className="panel-section">
            <h3><Filter size={14} /> {t('spatialIntelligence.sidebar.smartFilters')}</h3>
            <div className="filter-grid">
              <div className="filter-field">
                <label>{t('spatialIntelligence.filter.district')}</label>
                <select value={filters.district} onChange={(e) => handleFilterChange('district', e.target.value)}>
                  <option value="all">{t('spatialIntelligence.filter.allDistricts')}</option>
                  {districts.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div className="filter-field">
                <label>{t('spatialIntelligence.filter.category')}</label>
                <select value={filters.category} onChange={(e) => handleFilterChange('category', e.target.value)}>
                  <option value="all">{t('spatialIntelligence.filter.allCategories')}</option>
                  {categories.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div className="filter-field">
                <label>{t('spatialIntelligence.filter.priority')}</label>
                <select value={filters.priority} onChange={(e) => handleFilterChange('priority', e.target.value)}>
                  <option value="all">{t('spatialIntelligence.filter.allPriorities')}</option>
                  <option value="critical">{t('common.priority.critical')}</option>
                  <option value="high">{t('common.priority.high')}</option>
                  <option value="medium">{t('common.priority.medium')}</option>
                  <option value="low">{t('common.priority.low')}</option>
                </select>
              </div>
              <div className="filter-field">
                <label>{t('spatialIntelligence.filter.department')}</label>
                <select value={filters.department} onChange={(e) => handleFilterChange('department', e.target.value)}>
                  <option value="all">{t('spatialIntelligence.filter.allDepartments')}</option>
                  {departments.map((d) => (
                    <option key={d} value={d}>{t(getDeptI18nKey(d))}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="panel-section">
            <h3><Calendar size={14} /> {t('spatialIntelligence.sidebar.forecastTimeline')}</h3>
            <div className="timeline-buttons">
              {[7, 15, 30].map((days) => (
                <button
                  key={days}
                  className={`timeline-btn ${timelineDays === days ? 'active' : ''}`}
                  onClick={() => setTimelineDays(days)}
                >
                  {days} {t('spatialIntelligence.days')}
                </button>
              ))}
            </div>
            {forecast && (
              <div className="forecast-summary">
                <p><Activity size={12} /> {t('spatialIntelligence.forecastLoaded', { days: timelineDays })}</p>
              </div>
            )}
          </div>

          <div className="panel-section">
            <h3><MapPin size={14} /> {t('spatialIntelligence.sidebar.heatmapLegend')}</h3>
            <div className="legend-items">
              {[
                { color: '#22c55e', label: t('spatialIntelligence.legend.low') },
                { color: '#eab308', label: t('spatialIntelligence.legend.medium') },
                { color: '#f97316', label: t('spatialIntelligence.legend.high') },
                { color: '#ef4444', label: t('spatialIntelligence.legend.critical') },
              ].map(({ color, label }) => (
                <div key={label} className="legend-item">
                  <div className="legend-dot" style={{ background: color }} />
                  <span>{label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="panel-section">
            <h3><Radio size={14} /> {t('spatialIntelligence.sidebar.hotspots')}</h3>
            <div className="legend-items">
              <div className="legend-item">
                <div className="legend-dot hotspot" />
                <span>{t('spatialIntelligence.legend.activeHotspot')}</span>
              </div>
            </div>
          </div>
        </aside>

        <div className="command-map">
          <MapContainer
            key={mapKey}
            center={[11.0168, 76.9558]}
            zoom={13}
            style={{ height: '100%', width: '100%' }}
            zoomControl={false}
            attributionControl={false}
            maxBounds={COIMBATORE_BOUNDS}
            minZoom={11}
            maxZoom={18}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              maxZoom={19}
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />

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
                        <span style="color:#94a3b8;">${t('spatialIntelligence.districtComplaints')}</span> <strong>${districtData[districtName].count || 0}</strong><br/>
                        <span style="color:#94a3b8;">${t('spatialIntelligence.districtCritical')}</span> <strong style="color:#ef4444;">${districtData[districtName].criticalCount || 0}</strong>
                      </div>`,
                      { sticky: true, className: 'district-tooltip' }
                    );
                  }
                }}
              />
            )}

            {geofences.length > 0 && geofences.map((gf: any) => (
              <Circle
                key={gf.id}
                center={[gf.lat, gf.lng]}
                radius={gf.radius_meters}
                pathOptions={{
                  color: '#22c55e',
                  fillColor: '#22c55e',
                  fillOpacity: 0.08,
                  weight: 2,
                  dashArray: '5, 5',
                }}
              >
                <Tooltip direction="top" className="geofence-tooltip">
                  <strong>{gf.label}</strong><br />
                  <span style={{ color: '#94a3b8', fontSize: 11 }}>{gf.radius_meters}m radius</span>
                </Tooltip>
              </Circle>
            ))}

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
              const lat = hotspot.lat ?? hotspot.latitude ?? hotspot.y;
              const lng = hotspot.lng ?? hotspot.longitude ?? hotspot.x;
              if (lat == null || lng == null) return null;
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
                      <h4>{t('spatialIntelligence.hotspotTitle', { number: idx + 1 })}</h4>
                      <p><strong>{t('spatialIntelligence.hotspotIntensity')}</strong> {hotspot.count || hotspot.intensity || t('spatialIntelligence.hotspotNA')}</p>
                      {hotspot.category && <p><strong>{t('spatialIntelligence.hotspotCategory')}</strong> {hotspot.category}</p>}
                      {hotspot.ward && <p><strong>{t('spatialIntelligence.hotspotWard')}</strong> {hotspot.ward}</p>}
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

            <ComplaintClusterLayer pins={complaintPins} visible={layers.complaintPins} />
            {showGeoClusters && geoClusters.map((c: any, i: number) => (
              <Circle key={i} center={c.center as [number, number]} radius={300} pathOptions={{color: getPriorityColor(c.category), fillOpacity: 0.15, weight: 2}}>
                <Popup>
                  <strong>{c.count} {t('spatialIntelligence.geoClusterIncidents')}</strong><br/>
                  {t('spatialIntelligence.geoClusterCategory')} {c.category}<br/>
                  {c.incidents.slice(0, 3).map((inc: any) => `${inc.id || inc.incident_number || ''}`).join(', ')}
                </Popup>
              </Circle>
            ))}
          </MapContainer>

          <div className="map-overlay-info">
            <span className="map-source">{t('spatialIntelligence.mapSource')}</span>
            {error && <span className="map-warning"><AlertTriangle size={12} /> {t('spatialIntelligence.partialData')}</span>}
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
                  <span className="detail-label">{t('spatialIntelligence.detail.complaints')}</span>
                  <span className="detail-value">{selectedDistrictData.count || 0}</span>
                </div>
                <div className="detail-card">
                  <span className="detail-label">{t('spatialIntelligence.detail.riskScore')}</span>
                  <span className={`detail-value ${(selectedDistrictData.riskScore || 0) > 70 ? 'critical' : (selectedDistrictData.riskScore || 0) > 40 ? 'warning' : 'good'}`}>
                    {selectedDistrictData.riskScore || 0}%
                  </span>
                </div>
                <div className="detail-card">
                  <span className="detail-label">{t('spatialIntelligence.detail.healthScore')}</span>
                  <span className={`detail-value ${(selectedDistrictData.healthScore || 100) < 50 ? 'critical' : (selectedDistrictData.healthScore || 100) < 70 ? 'warning' : 'good'}`}>
                    {selectedDistrictData.healthScore || 100}%
                  </span>
                </div>
                <div className="detail-card">
                  <span className="detail-label">{t('spatialIntelligence.detail.criticalIncidents')}</span>
                  <span className="detail-value critical">{selectedDistrictData.criticalCount || 0}</span>
                </div>
              </div>

              <div className="detail-section">
                <h4><Target size={14} /> {t('spatialIntelligence.detail.topCategory')}</h4>
                <p className="detail-text">{getTopCategory(selectedDistrict)}</p>
              </div>

              <div className="detail-section">
                <h4><Brain size={14} /> {t('spatialIntelligence.detail.aiRecommendation')}</h4>
                <p className="detail-text recommendation">{generateAIRecommendation(selectedDistrict)}</p>
              </div>

              <div className="detail-section">
                <h4><Zap size={14} /> {t('spatialIntelligence.detail.resourceSimulation')}</h4>
                <div className="sim-controls">
                  <button className="sim-btn" onClick={() => handleSimulate(2)} disabled={simulating}>
                    {simulating ? <RefreshCw size={14} className="spin" /> : <Users size={14} />} {t('spatialIntelligence.simPlusTeams', { count: 2 })}
                  </button>
                  <button className="sim-btn" onClick={() => handleSimulate(5)} disabled={simulating}>
                    {simulating ? <RefreshCw size={14} className="spin" /> : <Users size={14} />} {t('spatialIntelligence.simPlusTeams', { count: 5 })}
                  </button>
                </div>
                {simResult && (
                  <div className="sim-result">
                    <p><strong>{t('spatialIntelligence.simResult')}</strong></p>
                    <pre>{JSON.stringify(simResult, null, 2)}</pre>
                  </div>
                )}
              </div>

              <div className="detail-section">
                <h4><AlertOctagon size={14} /> {t('spatialIntelligence.detail.incidentsInDistrict')}</h4>
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
                      <span className="incident-meta"><Clock size={10} /> {inc.days_open || 0}{t('spatialIntelligence.daysOpenUnit')}</span>
                    </div>
                  ))}
                  {(selectedDistrictData.incidents || []).length === 0 && (
                    <p className="no-data">{t('spatialIntelligence.noIncidentsDistrict')}</p>
                  )}
                </div>
              </div>
            </div>
          </aside>
        )}
      </div>

      <footer className="command-footer">
        <div className="footer-left">
          <span className="footer-brand">{t('spatialIntelligence.footer.brand')}</span>
          <span className="footer-status">
            <span className="status-dot" /> {t('spatialIntelligence.footer.systemOperational')}
          </span>
        </div>
        <div className="footer-right">
          <span>{t('spatialIntelligence.footer.dataRefreshed')}: {new Date().toLocaleString(dateLocale)}</span>
          <span className="footer-badge">{t('spatialIntelligence.footer.stateBadge')}</span>
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
              <span className="popup-label">{t('spatialIntelligence.popup.category')}</span>
              <span className="popup-value">{selectedIncident.category || 'N/A'}</span>
            </div>
            <div className="popup-row">
              <span className="popup-label">{t('spatialIntelligence.popup.priority')}</span>
              <span className={`popup-value priority-${selectedIncident.priority_label?.toLowerCase() || 'medium'}`}>
                {selectedIncident.priority_label || t('common.na')}
              </span>
            </div>
            <div className="popup-row">
              <span className="popup-label">{t('spatialIntelligence.popup.age')}</span>
              <span className="popup-value">{selectedIncident.days_open || 0} {t('spatialIntelligence.days')}</span>
            </div>
            <div className="popup-row">
              <span className="popup-label">{t('spatialIntelligence.popup.affectedPopulation')}</span>
              <span className="popup-value">{(selectedIncident.population || selectedIncident.cluster_size || 0).toLocaleString()}</span>
            </div>
            <div className="popup-row">
              <span className="popup-label">{t('spatialIntelligence.popup.recommendedAction')}</span>
              <span className="popup-value">{selectedIncident.recommended_action || t('spatialIntelligence.popup.pendingReview')}</span>
            </div>
          </div>
          <div className="popup-footer">
            <button className="open-details-btn" onClick={() => { window.location.href = '/incident-feed'; }}>
              {t('spatialIntelligence.popup.openDetails')} <ArrowUpRight size={14} />
            </button>
          </div>
        </div>
      )}

      {compareOpen && (
        <div className="modal-overlay" onClick={() => setCompareOpen(false)}>
          <div className="digest-modal-content compare-modal" onClick={e => e.stopPropagation()}>
            <div className="panel-header">
              <h3>{t('spatialIntelligence.compareTitle')}</h3>
              <button className="close-panel" onClick={() => setCompareOpen(false)}><X size={18} /></button>
            </div>
            {compareData ? (
              <div className="compare-grid">
                <div className="compare-col">
                  <h4>{t('spatialIntelligence.compareCurrent')}</h4>
                  <p>{t('spatialIntelligence.compareComplaints')}: {(compareData.current || []).reduce((s: number, h: any) => s + (h.count || 0), 0)}</p>
                  <p>{t('spatialIntelligence.compareIncidents')}: {incidents.length}</p>
                  <p>{t('spatialIntelligence.compareCritical')}: {criticalCount}</p>
                </div>
                <div className="compare-col">
                  <h4>{t('spatialIntelligence.comparePrevious')}</h4>
                  <p className="text-muted">{t('spatialIntelligence.compareHistoricalNote')}</p>
                </div>
              </div>
            ) : (
              <p className="text-muted">{t('spatialIntelligence.compareNoData')}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SpatialIntelligence;
