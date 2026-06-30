import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import Sidebar from './components/Sidebar';
import Analysis from './pages/Analysis';
import CitizenPortal from './pages/CitizenPortal';
import Clusters from './pages/Clusters';
import ExecutiveDashboard from './pages/ExecutiveDashboard';
import IncidentFeed from './pages/IncidentFeed';
import Landing from './pages/Landing';
import Methodology from './pages/Methodology';
import Overview from './pages/Overview';
import RoleSelection from './pages/RoleSelection';
import SpatialIntelligence from './pages/SpatialIntelligence';
import './App.css';

const PageTransition = ({ children }: { children: React.ReactNode }) => (
  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3 }}>
    {children}
  </motion.div>
);

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<PageTransition><Landing /></PageTransition>} />
        <Route path="/roles" element={<PageTransition><RoleSelection /></PageTransition>} />
        <Route path="/citizen" element={<PageTransition><CitizenPortal /></PageTransition>} />
        <Route path="/officer" element={<PageTransition><Overview /></PageTransition>} />
        <Route path="/executive" element={<PageTransition><ExecutiveDashboard /></PageTransition>} />
        <Route path="/incident-feed" element={<PageTransition><IncidentFeed /></PageTransition>} />
        <Route path="/analysis" element={<PageTransition><Analysis /></PageTransition>} />
        <Route path="/clusters" element={<PageTransition><Clusters /></PageTransition>} />
        <Route path="/spatial" element={<PageTransition><SpatialIntelligence /></PageTransition>} />
        <Route path="/methodology" element={<PageTransition><Methodology /></PageTransition>} />
      </Routes>
    </AnimatePresence>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <AnimatedRoutes />
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
