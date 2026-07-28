import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { ArrowLeft, Star, MapPin, Clock, AlertCircle, Loader2, X, ChevronLeft, ChevronRight } from 'lucide-react';
import './ResolvedGallery.css';

interface GalleryItem {
  id: string;
  category: string;
  ward: string;
  resolution_note: string | null;
  days_open: number;
  rating: number;
  resolution_photo_url: string | null;
}

const CATEGORY_COLORS: Record<string, string> = {
  'Roads': '#3b82f6',
  'Water Supply': '#06b6d4',
  'Waste Management': '#f59e0b',
  'Sanitation': '#16a34a',
  'Street Lighting': '#8b5cf6',
  'Electricity': '#dc2626',
  'Public Health': '#ea580c',
};

const ResolvedGallery = () => {
  const { t } = useTranslation();
  const [items, setItems] = useState<GalleryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lightboxIdx, setLightboxIdx] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getResolvedGallery()
      .then(data => { if (!cancelled) setItems(Array.isArray(data) ? data : []); })
      .catch(e => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const openLightbox = (idx: number) => setLightboxIdx(idx);
  const closeLightbox = () => setLightboxIdx(null);

  if (loading) return (
    <div className="resolved-gallery-page">
      <div className="gallery-container">
        <div className="page-loading"><Loader2 size={32} className="spin" /><span>{t('resolvedGallery.loading')}</span></div>
      </div>
    </div>
  );

  if (error) return (
    <div className="resolved-gallery-page">
      <div className="gallery-container">
        <div className="page-error"><AlertCircle size={20} /> {error}</div>
      </div>
    </div>
  );

  return (
    <div className="resolved-gallery-page">
      <div className="gallery-container">
        <Link to="/" className="gallery-back"><ArrowLeft size={16} /> {t('resolvedGallery.backButton')}</Link>

        <div className="gallery-header">
          <h1>{t('resolvedGallery.title')}</h1>
          <p>{t('resolvedGallery.subtitle')}</p>
        </div>

        {items.length === 0 ? (
          <div className="gallery-empty">
            <p>{t('resolvedGallery.empty')}</p>
          </div>
        ) : (
          <div className="gallery-grid">
            {items.map((item, idx) => (
              <div key={item.id} className="gallery-card">
                <div
                  className="gallery-photo"
                  onClick={() => openLightbox(idx)}
                  style={{ cursor: 'pointer' }}
                >
                  {item.resolution_photo_url ? (
                    <img
                      src={item.resolution_photo_url}
                      alt={`Resolved ${item.category}`}
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                  ) : (
                    <div className="gallery-photo-placeholder">
                      <Clock size={32} />
                    </div>
                  )}
                </div>
                <div className="gallery-card-body">
                  <div className="gallery-card-top">
                    <span
                      className="gallery-category-badge"
                      style={{ background: CATEGORY_COLORS[item.category] || '#64748b' }}
                    >
                      {item.category}
                    </span>
                    <span className="gallery-rating">
                      {[1, 2, 3, 4, 5].map(n => (
                        <Star key={n} size={14} className={n <= item.rating ? 'star-filled' : 'star-empty'} />
                      ))}
                    </span>
                  </div>
                  <div className="gallery-meta">
                    <span><MapPin size={12} /> {t('resolvedGallery.ward', { ward: item.ward })}</span>
                    <span><Clock size={12} /> {t('resolvedGallery.resolvedIn', { days: item.days_open })}</span>
                  </div>
                  {item.resolution_note && (
                    <p className="gallery-note">{item.resolution_note}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {lightboxIdx !== null && items[lightboxIdx]?.resolution_photo_url && (
        <div className="gallery-lightbox" onClick={closeLightbox}>
          <button className="lightbox-close" onClick={closeLightbox}><X size={24} /></button>
          <button
            className="lightbox-nav lightbox-prev"
            onClick={(e) => { e.stopPropagation(); setLightboxIdx(prev => prev !== null && prev > 0 ? prev - 1 : items.length - 1); }}
          ><ChevronLeft size={32} /></button>
          <img
            src={items[lightboxIdx].resolution_photo_url!}
            alt="Resolution"
            onClick={(e) => e.stopPropagation()}
            className="lightbox-img"
          />
          <button
            className="lightbox-nav lightbox-next"
            onClick={(e) => { e.stopPropagation(); setLightboxIdx(prev => prev !== null && prev < items.length - 1 ? prev + 1 : 0); }}
          ><ChevronRight size={32} /></button>
        </div>
      )}
    </div>
  );
};

export default ResolvedGallery;