import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Overview from './pages/Overview';
import IncidentFeed from './pages/IncidentFeed';
import Analysis from './pages/Analysis';
import Clusters from './pages/Clusters';
import Methodology from './pages/Methodology';
import CitizenPortal from './pages/CitizenPortal';
import ExecutiveDashboard from './pages/ExecutiveDashboard';
import SpatialIntelligence from './pages/SpatialIntelligence';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/executive" element={<ExecutiveDashboard />} />
            <Route path="/incidents" element={<IncidentFeed />} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/clusters" element={<Clusters />} />
            <Route path="/spatial" element={<SpatialIntelligence />} />
            <Route path="/methodology" element={<Methodology />} />
            <Route path="/citizen" element={<CitizenPortal />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
