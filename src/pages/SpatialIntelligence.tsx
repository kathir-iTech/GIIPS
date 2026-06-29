import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import './SpatialIntelligence.css';

const SpatialIntelligence = () => {
  const [heatmap, setHeatmap] = useState([]);
  const [forecast, setForecast] = useState([]);
  const [simulation, setSimulation] = useState<any>(null);

  useEffect(() => {
    api.getHeatmap().then(setHeatmap);
    api.getForecast(7).then(setForecast);
  }, []);

  const runSim = (teams: number) => api.simulateResources(teams).then(setSimulation);

  return (
    <div className="spatial-page">
      <h1>Spatial Intelligence</h1>
      <div className="grid">
        <div className="card"><h3>Heatmap</h3>{JSON.stringify(heatmap)}</div>
        <div className="card"><h3>Forecast</h3>{JSON.stringify(forecast)}</div>
        <div className="card">
            <h3>Resource Simulation</h3>
            <button onClick={() => runSim(2)}>Simulate 2 Teams</button>
            {simulation && <div>{simulation.projectedImpact}</div>}
        </div>
      </div>
    </div>
  );
};
export default SpatialIntelligence;
