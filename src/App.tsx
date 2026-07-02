import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { AuthProvider, useAuth } from './context/AuthContext';
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
import Login from './pages/Login';
import Register from './pages/Register';
import Unauthorized from './pages/Unauthorized';
import MyComplaints from './pages/MyComplaints';
import ComplaintDetail from './pages/ComplaintDetail';
import CitizenProfile from './pages/CitizenProfile';
import { ProtectedRoute, RoleGuard } from './components/ProtectedRoute';
import './App.css';

const PageTransition = ({ children }: { children: React.ReactNode }) => (
  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3 }}>
    {children}
  </motion.div>
);

const PUBLIC_NO_SIDEBAR = ['/', '/login', '/register'];

function AppLayout() {
  const { user } = useAuth();
  const location = useLocation();
  const showSidebar = user && !PUBLIC_NO_SIDEBAR.includes(location.pathname);

  return (
    <div className={showSidebar ? 'app-layout' : 'full-content'}>
      {showSidebar && <Sidebar />}
      <main className="main-content">
        <AnimatedRoutes />
      </main>
    </div>
  );
}

const AuthRedirect = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  if (user) {
    if (user.role === 'Citizen') return <Navigate to="/citizen" replace />;
    if (user.role === 'Officer') return <Navigate to="/officer" replace />;
    if (user.role === 'Executive') return <Navigate to="/executive" replace />;
  }
  return <>{children}</>;
};

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<PageTransition><Landing /></PageTransition>} />
        <Route path="/roles" element={<PageTransition><ProtectedRoute><RoleSelection /></ProtectedRoute></PageTransition>} />
        
        <Route path="/login" element={<PageTransition><AuthRedirect><Login /></AuthRedirect></PageTransition>} />
        <Route path="/register" element={<PageTransition><AuthRedirect><Register /></AuthRedirect></PageTransition>} />
        
        <Route path="/citizen" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Citizen']}>
              <CitizenPortal />
            </RoleGuard>
          </PageTransition>
        } />
        <Route path="/my-complaints" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Citizen']}>
              <MyComplaints />
            </RoleGuard>
          </PageTransition>
        } />
        <Route path="/complaint/:id" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Citizen']}>
              <ComplaintDetail />
            </RoleGuard>
          </PageTransition>
        } />
        <Route path="/profile" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Citizen']}>
              <CitizenProfile />
            </RoleGuard>
          </PageTransition>
        } />
        
        <Route path="/officer" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Officer']}>
              <Overview />
            </RoleGuard>
          </PageTransition>
        } />
        
        <Route path="/executive" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Executive']}>
              <ExecutiveDashboard />
            </RoleGuard>
          </PageTransition>
        } />
        
        <Route path="/incident-feed" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Officer', 'Executive']}>
              <IncidentFeed />
            </RoleGuard>
          </PageTransition>
        } />
        
        <Route path="/analysis" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Officer', 'Executive']}>
              <Analysis />
            </RoleGuard>
          </PageTransition>
        } />
        
        <Route path="/clusters" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Officer', 'Executive']}>
              <Clusters />
            </RoleGuard>
          </PageTransition>
        } />
        
        <Route path="/spatial" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Officer', 'Executive']}>
              <SpatialIntelligence />
            </RoleGuard>
          </PageTransition>
        } />
        
        <Route path="/methodology" element={
          <PageTransition>
            <Methodology />
          </PageTransition>
        } />
        
        <Route path="/unauthorized" element={
          <PageTransition>
            <Unauthorized />
          </PageTransition>
        } />
      </Routes>
    </AnimatePresence>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppLayout />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
