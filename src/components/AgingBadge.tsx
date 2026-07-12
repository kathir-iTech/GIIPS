import { getAgingLevel } from '../constants/aging';

export const AgingBadge = ({ daysOpen }: { daysOpen: number }) => {
  const level = getAgingLevel(daysOpen);
  return <span className={`aging-badge aging-${level}`}>{daysOpen}d</span>;
};
