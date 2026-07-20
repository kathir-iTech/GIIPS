import { useTranslation } from 'react-i18next';
import { Check } from 'lucide-react';
import './StatusTimeline.css';

export interface Stage {
  key: string;
  label: string;
  date?: string | null;
  active: boolean;
  isLast?: boolean;
}

interface Props {
  stages: Stage[];
}

export function StatusTimeline({ stages }: Props) {
  return (
    <div className="status-timeline">
      {stages.map((s, i) => (
        <div key={s.key} className={`st-stage ${s.active ? 'active' : ''} ${i === stages.length - 1 ? 'last' : ''}`}>
          <div className="st-marker">
            <div className="st-dot">
              {s.active ? <Check size={10} /> : null}
            </div>
            {i < stages.length - 1 && <div className="st-line" />}
          </div>
          <div className="st-content">
            <span className="st-label">{s.label}</span>
            {s.date && <span className="st-date">{new Date(s.date).toLocaleDateString('en-IN')}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

export function useStatusStages(
  dateReceived: string | null | undefined,
  incidentStatus: string | null | undefined,
  hasOfficer: boolean,
  hasCategory: boolean,
) {
  const { t } = useTranslation();
  const status = incidentStatus || 'pending';
  const hasIncident = status !== 'pending';
  const isResolved = ['resolved', 'pending_verification', 'closed'].includes(status);
  const isInProgress = isResolved || status === 'in-progress';
  const isRouted = isInProgress || (hasIncident && hasOfficer);
  const isVerified = isRouted || hasIncident;

  return [
    { key: 'received', label: t('complaintDetail.stageReceived'), date: dateReceived, active: true },
    { key: 'verified', label: t('complaintDetail.stageVerified'), date: dateReceived, active: isVerified },
    { key: 'routed', label: t('complaintDetail.stageRouted'), date: null, active: isRouted },
    { key: 'inProgress', label: t('complaintDetail.stageInProgress'), date: null, active: isInProgress },
    { key: 'resolved', label: t('complaintDetail.stageResolved'), date: null, active: isResolved },
  ];
}
