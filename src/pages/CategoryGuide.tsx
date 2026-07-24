import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ArrowLeft, Road, Droplets, Trash2, Droplet, Lightbulb, Zap, Heart } from 'lucide-react';
import './CategoryGuide.css';

const CATEGORY_KEYS = [
  { key: 'roads', icon: Road },
  { key: 'waterSupply', icon: Droplets },
  { key: 'wasteManagement', icon: Trash2 },
  { key: 'sanitation', icon: Droplet },
  { key: 'streetLighting', icon: Lightbulb },
  { key: 'electricity', icon: Zap },
  { key: 'publicHealth', icon: Heart },
];

const CategoryGuide = () => {
  const { t } = useTranslation();

  return (
    <div className="cat-guide-page">
      <div className="cat-guide-container">
        <Link to="/" className="cat-guide-back">
          <ArrowLeft size={16} /> {t('categoryGuide.backLink')}
        </Link>

        <div className="cat-guide-header">
          <h1>{t('categoryGuide.title')}</h1>
          <p>{t('categoryGuide.subtitle')}</p>
        </div>

        <div className="cat-guide-grid">
          {CATEGORY_KEYS.map(({ key, icon: Icon }) => (
            <div key={key} className="cat-guide-card">
              <div className="cat-guide-icon"><Icon size={22} /></div>
              <div className="cat-guide-body">
                <h3>{t(`categoryGuide.categories.${key}.name`)}</h3>
                <p className="cat-guide-desc">{t(`categoryGuide.categories.${key}.desc`)}</p>
                <div className="cat-guide-examples">
                  <span className="cat-guide-examples-label">Examples:</span>
                  <span>{t(`categoryGuide.categories.${key}.example`)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="cat-guide-help">
          <Heart size={14} />
          <span>{t('categoryGuide.helpLabel')}</span>
        </div>
      </div>
    </div>
  );
};

export default CategoryGuide;
