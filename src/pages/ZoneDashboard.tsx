import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { getCoimbatoreZone } from '../data/coimbatoreZones';
import Header from '../components/Header';
import { MapPin, Building2, AlertTriangle, ChevronDown, ChevronUp, Activity } from 'lucide-react';
import './Admin.css';

const ZONE_NAMES = ['North', 'East', 'Central', 'West', 'South'];

const ZoneDashboard = () => {
  const { t } = useTranslation();
  const [wardHealth, setWardHealth] = useState<any[]>([]);
  const [deptWorkload, setDeptWorkload] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedZone, setExpandedZone] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getWardHealth().catch(() => []),
      api.getDeptWorkload().catch(() => []),
    ]).then(([wh, dw]) => {
      setWardHealth(wh || []);
      setDeptWorkload(dw || []);
    }).finally(() => setLoading(false));
  }, []);

  const zoneData = useMemo(() => {
    const zones: Record<string, {
      wards: string[];
      openIncidents: number;
      slaCompliance: number;
      categoryCounts: Record<string, number>;
      wardHealthMap: Record<string, number>;
    }> = {};

    ZONE_NAMES.forEach(z => {
      zones[z] = {
        wards: [],
        openIncidents: 0,
        slaCompliance: 100,
        categoryCounts: {},
        wardHealthMap: {},
      };
    });

    wardHealth.forEach((w: any) => {
      const zone = getCoimbatoreZone(w.ward ?? w.district ?? w.name);
      if (!zone || !zones[zone]) return;
      zones[zone].wards.push(w.ward || w.name || 'Unknown');
      zones[zone].openIncidents += w.open_incidents || w.openIncidents || 0;
      zones[zone].wardHealthMap[w.ward || w.name || ''] = w.healthScore ?? w.health_score ?? 100;
    });

    deptWorkload.forEach((d: any) => {
      const cat = d.category || d.department || 'Unknown';
      // departments aren't zone-specific, so we distribute by zone proportionally
      const totalInc = d.open_incidents || d.openIncidents || 0;
      const zoneCount = ZONE_NAMES.length;
      const perZone = Math.round(totalInc / zoneCount);
      ZONE_NAMES.forEach(z => {
        zones[z].categoryCounts[cat] = (zones[z].categoryCounts[cat] || 0) + perZone;
      });
    });

    return ZONE_NAMES.map(zone => {
      const z = zones[zone];
      const entries = Object.entries(z.categoryCounts);
      entries.sort((a, b) => b[1] - a[1]);
      const topCategory = entries.length > 0 ? entries[0][0] : '—';

      const healthEntries = Object.entries(z.wardHealthMap);
      healthEntries.sort((a, b) => a[1] - b[1]);
      const worstWard = healthEntries.length > 0 ? healthEntries[0][0] : '—';

      const slaCompliance = z.openIncidents > 0
        ? Math.max(0, 100 - Math.round(z.openIncidents * 0.5))
        : 100;

      return {
        name: zone,
        wards: z.wards,
        openIncidents: z.openIncidents,
        slaCompliance,
        topCategory,
        worstWard,
      };
    });
  }, [wardHealth, deptWorkload]);

  if (loading) return <div className="page-loading"><div className="spinner"></div><span>{t('common.loading')}</span></div>;

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>{t('executive.zoneDashboard')}</h1>
        <p>Coimbatore — Zone-level performance overview</p>
      </div>

      <div className="zone-dashboard-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
        {zoneData.map(zone => (
          <div key={zone.name} className="dept-card" style={{ cursor: 'pointer' }}
            onClick={() => setExpandedZone(expandedZone === zone.name ? null : zone.name)}>
            <div className="dept-header">
              <Building2 size={24} />
              <h3>{zone.name} Zone</h3>
            </div>
            <div className="dept-stats">
              <div className="stat">
                <span className="value">{zone.openIncidents}</span>
                <span className="label">{t('executive.openIncidents')}</span>
              </div>
              <div className="stat">
                <span className="value" style={{ color: zone.slaCompliance >= 80 ? '#16a34a' : zone.slaCompliance >= 50 ? '#ca8a04' : '#dc2626' }}>{zone.slaCompliance}%</span>
                <span className="label">{t('executive.slaCompliance')}</span>
              </div>
              <div className="stat">
                <span className="value" style={{ fontSize: '0.8rem' }}>{zone.topCategory}</span>
                <span className="label">{t('executive.topCategory')}</span>
              </div>
              <div className="stat">
                <span className="value">{zone.worstWard}</span>
                <span className="label">{t('executive.worstWard')}</span>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              <MapPin size={12} /> {zone.wards.length} {t('executive.wards')}
              {expandedZone === zone.name ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </div>
            {expandedZone === zone.name && (
              <div style={{ marginTop: '0.75rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem' }}>
                <h4 style={{ fontSize: '0.85rem', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Wards</h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                  {zone.wards.map(ward => {
                    const health = wardHealth.find((w: any) => (w.ward === ward || w.name === ward));
                    const score = health?.healthScore ?? health?.health_score ?? 100;
                    const color = score >= 80 ? '#16a34a' : score >= 50 ? '#ca8a04' : '#dc2626';
                    return (
                      <span key={ward} style={{
                        padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem',
                        background: `${color}18`, color, border: `1px solid ${color}40`,
                      }}>
                        {ward}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ZoneDashboard;
