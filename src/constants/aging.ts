export const AGING = {
  WARNING_DAYS: 4,
  CRITICAL_DAYS: 8,
  SEVERE_DAYS: 30,
} as const;

export type AgingLevel = 'normal' | 'warning' | 'critical' | 'severe';

export function getAgingLevel(daysOpen: number): AgingLevel {
  if (daysOpen >= AGING.SEVERE_DAYS) return 'severe';
  if (daysOpen >= AGING.CRITICAL_DAYS) return 'critical';
  if (daysOpen >= AGING.WARNING_DAYS) return 'warning';
  return 'normal';
}
