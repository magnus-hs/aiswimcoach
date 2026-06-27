import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * ProtectedRoute component that checks authentication status.
 * Redirects to /login if the user is not authenticated.
 * Shows nothing while checking authentication status.
 * 
 * Validates: Requirements 22.1-22.5, 16.2, 19.2
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();

  // Wait for auth check to complete
  if (isLoading) {
    return null; // or return a loading spinner
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
