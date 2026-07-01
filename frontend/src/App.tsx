import { useState, useRef, useCallback } from 'react';
import { Routes, Route, Navigate, useLocation, useParams } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Navigation } from './components/Navigation';
import { SideNav } from './components/SideNav';
import { ProfileModal } from './components/ProfileModal';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { DashboardPage } from './pages/DashboardPage';
import { ActivityDetailPage } from './pages/ActivityDetailPage';
import { TrainingPlansPage } from './pages/TrainingPlansPage';
import { NewPlanPage } from './pages/NewPlanPage';
import { PersonalBestsPage } from './pages/PersonalBestsPage';
import { AbilityAssessmentPage } from './pages/AbilityAssessmentPage';
import { CSSPage } from './pages/CSSPage';
import { GoalsPage } from './pages/GoalsPage';
import { AIAnalysisPage } from './pages/AIAnalysisPage';
import { PlanDetailView } from './components/PlanDetailView';

/**
 * Redirect component for backward compatibility.
 * Redirects /session/:id to /activity/:id preserving the session ID.
 * Validates: Requirements 2.6
 */
function RedirectToActivity() {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/activity/${id}`} replace />;
}

function App() {
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  // ProfileModal state
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const profileTriggerRef = useRef<HTMLElement>(null!);

  const handleProfileClick = useCallback(() => {
    setIsProfileOpen(true);
  }, []);

  const handleProfileClose = useCallback(() => {
    setIsProfileOpen(false);
  }, []);

  // Determine if we should show sidebar layout
  const isPublicRoute = location.pathname === '/login' || location.pathname === '/register';
  const showSidebar = isAuthenticated && !isPublicRoute;
  const showNavigation = isAuthenticated && !isPublicRoute;

  return (
    <div className="app">
      {showNavigation && (
        <Navigation onProfileClick={handleProfileClick} profileButtonRef={profileTriggerRef} />
      )}
      <div className="app__body">
        {showSidebar && <SideNav />}
        <main className={`app-main ${showSidebar ? 'app-main--with-sidebar' : ''}`}>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />

          {/* Protected routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/activity/new"
            element={
              <ProtectedRoute>
                <ActivityDetailPage mode="upload" />
              </ProtectedRoute>
            }
          />
          <Route
            path="/activity/:id"
            element={
              <ProtectedRoute>
                <ActivityDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/plans"
            element={
              <ProtectedRoute>
                <TrainingPlansPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/plans/new"
            element={
              <ProtectedRoute>
                <NewPlanPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/plans/:planId"
            element={
              <ProtectedRoute>
                <PlanDetailView />
              </ProtectedRoute>
            }
          />
          <Route
            path="/personal-bests"
            element={
              <ProtectedRoute>
                <PersonalBestsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ability"
            element={
              <ProtectedRoute>
                <AbilityAssessmentPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/css"
            element={
              <ProtectedRoute>
                <CSSPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/goals"
            element={
              <ProtectedRoute>
                <GoalsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ai-coach"
            element={
              <ProtectedRoute>
                <AIAnalysisPage />
              </ProtectedRoute>
            }
          />

          {/* Backward compatibility: /session/:id → /activity/:id */}
          <Route
            path="/session/:id"
            element={
              <ProtectedRoute>
                <RedirectToActivity />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
      </div>
      <ProfileModal
        isOpen={isProfileOpen}
        onClose={handleProfileClose}
        triggerRef={profileTriggerRef}
      />
    </div>
  );
}

export default App;
