import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { AuthProvider, useAuth } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import LanguageSwitcher from './components/LanguageSwitcher';
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
const OfficerManagement = lazy(() => import('./pages/OfficerManagement'));
const DepartmentManagement = lazy(() => import('./pages/DepartmentManagement'));
const SystemHealth = lazy(() => import('./pages/SystemHealth'));
const AuditLogs = lazy(() => import('./pages/AuditLogs'));

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

const PageTransition = ({ children }: { children: React.ReactNode }) => (
  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3 }}>
    {children}
  </motion.div>
);

const PUBLIC_NO_SIDEBAR = ['/', '/login', '/register', '/citizen-services', '/government-portal'];

function AppLayout() {
  const { user } = useAuth();
  const location = useLocation();
  const showSidebar = user && !PUBLIC_NO_SIDEBAR.includes(location.pathname);

  return (
    <div className={showSidebar ? 'app-layout' : 'full-content'}>
      <LanguageSwitcher />
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
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<PageTransition><Landing /></PageTransition>} />
        
        <Route path="/login" element={<PageTransition><Login /></PageTransition>} />
        <Route path="/register" element={<PageTransition><Register /></PageTransition>} />
        <Route path="/citizen-services" element={<PageTransition><CitizenServices /></PageTransition>} />
        <Route path="/government-portal" element={<PageTransition><GovernmentPortal /></PageTransition>} />
        
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

        
        <Route path="/admin" element={<Navigate to="/admin/officers" replace />} />
        <Route path="/admin/officers" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Executive']}>
              <OfficerManagement />
            </RoleGuard>
          </PageTransition>
        } />
        <Route path="/admin/departments" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Executive']}>
              <DepartmentManagement />
            </RoleGuard>
          </PageTransition>
        } />
        <Route path="/admin/system-health" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Executive']}>
              <SystemHealth />
            </RoleGuard>
          </PageTransition>
        } />
        <Route path="/admin/audit-logs" element={
          <PageTransition>
            <RoleGuard allowedRoles={['Executive']}>
              <AuditLogs />
            </RoleGuard>
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
