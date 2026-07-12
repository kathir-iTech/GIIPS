export const AGING = {
  WARNING_DAYS: 4,
  CRITICAL_DAYS: 8,
} as const;

export type AgingLevel = 'normal' | 'warning' | 'critical';

export function getAgingLevel(daysOpen: number): AgingLevel {
  if (daysOpen >= AGING.CRITICAL_DAYS) return 'critical';
  if (daysOpen >= AGING.WARNING_DAYS) return 'warning';
  return 'normal';
}
