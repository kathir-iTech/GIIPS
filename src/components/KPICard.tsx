import type React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';
import './KPICard.css';

interface KPICardProps { 
  title: string; 
  value: string | number; 
  subtitle?: string; 
  variant?: 'default' | 'critical' | 'success';
  icon?: LucideIcon;
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
