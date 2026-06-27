import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Header } from './components/Header';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { UploadPage } from './pages/UploadPage';
import { ProfilePage } from './pages/ProfilePage';
import { HistoryPage } from './pages/HistoryPage';
import { SessionDetailPage } from './pages/SessionDetailPage';

/**
 * Root redirect component that redirects to /login or /upload based on auth state.
 * Validates: Requirements 22.1
 */
function RootRedirect() {
  const { isAuthenticated } = useAuth();
  return <Navigate to={isAuthenticated ? '/upload' : '/login'} replace />;
}

function App() {
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  // Determine if we should show sidebar layout
  const isPublicRoute = location.pathname === '/login' || location.pathname === '/register';
  const showSidebar = isAuthenticated && !isPublicRoute;

  return (
    <div className="app">
      <Header />
      <main className={`app-main ${showSidebar ? 'app-main--with-sidebar' : ''}`}>
        <Routes>
          {/* Root route - redirect based on auth state */}
          <Route path="/" element={<RootRedirect />} />
          
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          
          {/* Protected routes */}
          <Route
            path="/upload"
            element={
              <ProtectedRoute>
                <UploadPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <HistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/session/:id"
            element={
              <ProtectedRoute>
                <SessionDetailPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}

export default App;
