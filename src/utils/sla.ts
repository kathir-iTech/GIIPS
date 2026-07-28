import { getCoimbatoreZone } from '../data/coimbatoreZones';

export type SLAStatus = 'on_track' | 'delayed' | 'overdue';

export function getSLAStatus(daysOpen: number, ward?: string | null): SLAStatus {
  const zone = getCoimbatoreZone(ward);
  const slaDays = zone ? 5 : 2;
  if (daysOpen <= slaDays) return 'on_track';
  if (daysOpen <= slaDays * 1.5) return 'delayed';
  return 'overdue';
}

export function getSLAStatusLabel(status: SLAStatus, t: (key: string) => string): string {
  const labels: Record<SLAStatus, string> = {
    on_track: t('sla.onTrack'),
    delayed: t('sla.delayed'),
    overdue: t('sla.overdue'),
  };
  return labels[status];
}
