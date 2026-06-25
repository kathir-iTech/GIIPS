import type React from 'react';
import './KPICard.css';

interface KPICardProps { title: string; value: string | number; subtitle?: string; variant?: 'default' | 'critical' | 'success'; }

const KPICard: React.FC<KPICardProps> = ({ title, value, subtitle, variant = 'default' }) => (
  <div className={`kpi-card kpi-card--${variant}`}>
    <div className="kpi-header"><span className="kpi-title">{title}</span></div>
    <div className="kpi-body">
      <span className="kpi-value">{value}</span>
      {subtitle && <span className="kpi-subtitle">{subtitle}</span>}
    </div>
  </div>
);

export default KPICard;
