import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { AuthProvider, useAuth } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import LanguageSwitcher from './components/LanguageSwitcher';
import NotificationBell from './components/NotificationBell';
import { ErrorBoundary } from './components/ErrorBoundary';
import { RoleGuard } from './components/ProtectedRoute';
import './App.css';

const Analysis = lazy(() => import('./pages/Analysis'));
const CitizenPortal = lazy(() => import('./pages/CitizenPortal'));
const Clusters = lazy(() => import('./pages/Clusters'));
const ExecutiveDashboard = lazy(() => import('./pages/ExecutiveDashboard'));
const IncidentFeed = lazy(() => import('./pages/IncidentFeed'));
const Landing = lazy(() => import('./pages/Landing'));
const Methodology = lazy(() => import('./pages/Methodology'));
const Overview = lazy(() => import('./pages/Overview'));
const SpatialIntelligence = lazy(() => import('./pages/SpatialIntelligence'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Unauthorized = lazy(() => import('./pages/Unauthorized'));
const MyComplaints = lazy(() => import('./pages/MyComplaints'));
const ComplaintDetail = lazy(() => import('./pages/ComplaintDetail'));
const CitizenProfile = lazy(() => import('./pages/CitizenProfile'));
const CitizenServices = lazy(() => import('./pages/CitizenServices'));
const GovernmentPortal = lazy(() => import('./pages/GovernmentPortal'));
const TrackComplaint = lazy(() => import('./pages/TrackComplaint'));
const Transparency = lazy(() => import('./pages/Transparency'));
const CategoryGuide = lazy(() => import('./pages/CategoryGuide'));
const OfficerManagement = lazy(() => import('./pages/OfficerManagement'));
const DepartmentManagement = lazy(() => import('./pages/DepartmentManagement'));
const SystemHealth = lazy(() => import('./pages/SystemHealth'));
const AuditLogs = lazy(() => import('./pages/AuditLogs'));
const LocalAuthorityDashboard = lazy(() => import('./pages/LocalAuthorityDashboard'));
const OversightDashboard = lazy(() => import('./pages/OversightDashboard'));
const Notifications = lazy(() => import('./pages/Notifications'));
const ApiDocs = lazy(() => import('./pages/ApiDocs'));

function LoadingScreen() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', background: '#0a0e1a', color: '#94a3b8',
      fontFamily: 'inherit', fontSize: '14px'
    }}>
      <span>Loading...</span>
    </div>
  );
}

const PUBLIC_NO_SIDEBAR = ['/', '/login', '/register', '/citizen-services', '/government-portal', '/track', '/transparency', '/categories', '/api-docs'];

function AppLayout() {
  const { user } = useAuth();
  const location = useLocation();
  const showSidebar = user && !PUBLIC_NO_SIDEBAR.includes(location.pathname);

  return (
    <div className={showSidebar ? 'app-layout' : 'full-content'}>
      <div className="top-bar">
        <NotificationBell />
        <LanguageSwitcher />
      </div>
      {showSidebar && <Sidebar />}
      <main className="main-content">
        <ErrorBoundary>
          <Suspense fallback={<LoadingScreen />}>
            <AnimatedRoutes />
          </Suspense>
        </ErrorBoundary>
      </main>
    </div>
  );
}

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="popLayout">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.3 }}
      >
      <Routes location={location}>
        <Route path="/" element={<Landing />} />
        
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/citizen-services" element={<CitizenServices />} />
        <Route path="/government-portal" element={<GovernmentPortal />} />
        <Route path="/track" element={<TrackComplaint />} />
        <Route path="/transparency" element={<Transparency />} />
        <Route path="/categories" element={<CategoryGuide />} />
        <Route path="/api-docs" element={<ApiDocs />} />
        
        <Route path="/citizen" element={
          
            <RoleGuard allowedRoles={['Citizen']}>
              <CitizenPortal />
            </RoleGuard>
          
        } />
        <Route path="/my-complaints" element={
          
            <RoleGuard allowedRoles={['Citizen']}>
              <MyComplaints />
            </RoleGuard>
          
        } />
        <Route path="/complaint/:id" element={
          
            <RoleGuard allowedRoles={['Citizen']}>
              <ComplaintDetail />
            </RoleGuard>
          
        } />
        <Route path="/profile" element={
          
            <RoleGuard allowedRoles={['Citizen']}>
              <CitizenProfile />
            </RoleGuard>
          
        } />
        
        <Route path="/officer" element={
          
            <RoleGuard allowedRoles={['Officer']}>
              <Overview />
            </RoleGuard>
          
        } />
        
        <Route path="/executive" element={
          
            <RoleGuard allowedRoles={['Executive']}>
              <ExecutiveDashboard />
            </RoleGuard>
          
        } />
        
        <Route path="/incident-feed" element={
          
            <RoleGuard allowedRoles={['Officer', 'Executive', 'Commissioner']}>
              <IncidentFeed />
            </RoleGuard>
          
        } />
        
        <Route path="/analysis" element={
          
            <RoleGuard allowedRoles={['Officer', 'Executive', 'Commissioner', 'Collector']}>
              <Analysis />
            </RoleGuard>
          
        } />
        
        <Route path="/clusters" element={
          
            <RoleGuard allowedRoles={['Officer', 'Executive', 'Commissioner', 'Collector']}>
              <Clusters />
            </RoleGuard>
          
        } />
        
        <Route path="/spatial" element={
          
            <RoleGuard allowedRoles={['Officer', 'Executive', 'Commissioner', 'Collector']}>
              <SpatialIntelligence />
            </RoleGuard>
          
        } />
        
        <Route path="/local-authority" element={
          
            <RoleGuard allowedRoles={['Councillor', 'Commissioner']}>
              <LocalAuthorityDashboard />
            </RoleGuard>
          
        } />
        <Route path="/oversight" element={
          
            <RoleGuard allowedRoles={['MLA', 'Collector']}>
              <OversightDashboard />
            </RoleGuard>
          
        } />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/methodology" element={
          
            <Methodology />
          
        } />
        
        <Route path="/unauthorized" element={
          
            <Unauthorized />
          
        } />

        
        <Route path="/admin" element={<Navigate to="/admin/officers" replace />} />
        <Route path="/admin/officers" element={
          
            <RoleGuard allowedRoles={['Executive']}>
              <OfficerManagement />
            </RoleGuard>
          
        } />
        <Route path="/admin/departments" element={
          
            <RoleGuard allowedRoles={['Executive']}>
              <DepartmentManagement />
            </RoleGuard>
          
        } />
        <Route path="/admin/system-health" element={
          
            <RoleGuard allowedRoles={['Executive']}>
              <SystemHealth />
            </RoleGuard>
          
        } />
        <Route path="/admin/audit-logs" element={
          
            <RoleGuard allowedRoles={['Executive']}>
              <AuditLogs />
            </RoleGuard>
          
        } />
      </Routes>
      </motion.div>
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
