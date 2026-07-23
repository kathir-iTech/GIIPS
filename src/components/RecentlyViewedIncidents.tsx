import { ArrowUpRight, History, Trash2 } from 'lucide-react';
import type { RecentlyViewedIncident } from '../hooks/useRecentlyViewedIncidents';
import { useRecentlyViewedIncidents } from '../hooks/useRecentlyViewedIncidents';
import './RecentlyViewedIncidents.css';

interface RecentlyViewedIncidentsProps {
  onOpen: (incident: RecentlyViewedIncident) => void;
}

const RecentlyViewedIncidents = ({ onOpen }: RecentlyViewedIncidentsProps) => {
  const { items, clear } = useRecentlyViewedIncidents();

  return (
    <aside className="recently-viewed-card" aria-label="Recently viewed incidents">
      <div className="recently-viewed-header">
        <div className="recently-viewed-title">
          <History size={16} />
          <div>
            <h3>Recently viewed</h3>
            <p>Quick return to your last five incidents</p>
          </div>
        </div>
        {items.length > 0 && (
          <button className="recently-viewed-clear" onClick={clear} title="Clear recently viewed incidents">
            <Trash2 size={14} /> Clear
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <div className="recently-viewed-empty">Open an incident to add it here.</div>
      ) : (
        <div className="recently-viewed-list">
          {items.map(incident => (
            <button key={incident.id} className="recently-viewed-item" onClick={() => onOpen(incident)}>
              <span className={`recently-viewed-priority ${incident.priority_label.toLowerCase()}`} />
              <span className="recently-viewed-main">
                <strong>{incident.incident_number}</strong>
                <span>{incident.category} · {incident.ward}</span>
              </span>
              <span className="recently-viewed-source">{incident.source === 'Clusters' ? 'Workspace' : 'Feed'}</span>
              <ArrowUpRight size={14} />
            </button>
          ))}
        </div>
      )}
    </aside>
  );
};

export default RecentlyViewedIncidents;
