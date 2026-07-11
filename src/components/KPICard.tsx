import type React from 'react';
import { motion } from 'framer-motion';
import './KPICard.css';

type IconComponent = React.ComponentType<{ size?: number; className?: string }>;

interface KPICardProps { 
  title: string; 
  value: string | number; 
  subtitle?: string; 
  variant?: 'default' | 'critical' | 'success';
  icon?: IconComponent;
}

const KPICard: React.FC<KPICardProps> = ({ title, value, subtitle, variant = 'default', icon: Icon }) => (
  <motion.div 
    className={`kpi-card kpi-card--${variant}`}
    whileHover={{ y: -4 }}
  >
    <div className="kpi-title">
      {Icon && <Icon size={16} />}
      {title}
    </div>
    <div className="kpi-body">
      <motion.span 
        className="kpi-value"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        {value}
      </motion.span>
      {subtitle && <span className="kpi-subtitle">{subtitle}</span>}
    </div>
  </motion.div>
);

export default KPICard;
