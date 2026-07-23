import { useCallback, useEffect, useState } from 'react';
import type { Incident } from '../types';

const STORAGE_KEY = 'giips.officer.recentlyViewedIncidents';
const MAX_RECENT_ITEMS = 5;

export interface RecentlyViewedIncident {
  id: string;
  incident_number: string;
  category: string;
  ward: string;
  priority_label: Incident['priority_label'];
  source: 'IncidentFeed' | 'Clusters';
  viewedAt: number;
}

const readRecentlyViewed = (): RecentlyViewedIncident[] => {
  if (typeof window === 'undefined') return [];
  try {
    const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '[]');
    return Array.isArray(stored) ? stored.slice(0, MAX_RECENT_ITEMS) : [];
  } catch {
    return [];
  }
};

const writeRecentlyViewed = (items: RecentlyViewedIncident[]) => {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // Storage can be unavailable in private browsing; the in-memory list still works.
  }
};

export const useRecentlyViewedIncidents = () => {
  const [items, setItems] = useState<RecentlyViewedIncident[]>(readRecentlyViewed);

  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setItems(readRecentlyViewed());
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);

  const record = useCallback((incident: Incident, source: RecentlyViewedIncident['source']) => {
    setItems(previous => {
      const next: RecentlyViewedIncident[] = [
        {
          id: incident.id,
          incident_number: incident.incident_number,
          category: incident.category,
          ward: incident.ward,
          priority_label: incident.priority_label,
          source,
          viewedAt: Date.now(),
        },
        ...previous.filter(item => item.id !== incident.id),
      ].slice(0, MAX_RECENT_ITEMS);
      writeRecentlyViewed(next);
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    setItems([]);
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore storage failures.
    }
  }, []);

  return { items, record, clear };
};
