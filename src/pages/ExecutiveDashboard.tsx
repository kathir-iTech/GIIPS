import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import Header from '../components/Header';
import './ExecutiveDashboard.css';

const ExecutiveDashboard = () => {
  const [data, setData] = useState<any>(null);
  const [health, setHealth] = useState<any[]>([]);
  const [workload, setWorkload] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([
      api.getExecutiveSummary(),
      api.getWardHealth(),
      api.getDeptWorkload()
    ]).then(([sum, hel, work]) => {
      setData(sum);
      setHealth(hel);
      setWorkload(work);
    });
  }, []);

  if (!data) return <div>Loading...</div>;

  return (
    <div className="exec-dashboard">
      <Header title="Executive Decision Intelligence" subtitle="Government Decision Support System" />
      
      <section className="morning-brief">
        <h2>Executive Morning Brief</h2>
        <div className="brief-grid">
          <div className="brief-card critical"><strong>Critical Incidents:</strong> {data.criticalIncidentCount}</div>
          <div className="brief-card"><strong>Worst Ward:</strong> {data.worstPerformingWard}</div>
          <div className="brief-card"><strong>Emerging Issue:</strong> {data.emergingIssueCategory}</div>
          <div className="brief-card recommendation"><strong>Top Action:</strong> {data.topRecommendation}</div>
        </div>
      </section>

      <section className="analytics-grid">
        <div className="card">
          <h3>Ward Health Scores</h3>
          {health.map(h => <div key={h.ward}>{h.ward}: {h.healthScore}</div>)}
        </div>
        <div className="card">
          <h3>Department Workload</h3>
          {workload.map(w => <div key={w.department}>{w.department}: {w.activeIncidents}</div>)}
        </div>
      </section>
    </div>
  );
};

export default ExecutiveDashboard;
