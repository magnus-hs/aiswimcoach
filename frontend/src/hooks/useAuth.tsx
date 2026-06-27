import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface AuthState {
  token: string | null;
  user_id: string | null;
  email: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (token: string) => void;
  logout: () => void;
  register: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Decode JWT token to extract user_id and email from payload.
 * JWT format: header.payload.signature
 * Payload is base64url encoded JSON.
 */
function decodeToken(token: string): { user_id: string; email: string } | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      return null;
    }

    // Decode the payload (second part)
    const payload = parts[1];
    // Replace URL-safe characters and add padding if needed
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const paddedBase64 = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, '=');
    
    const jsonPayload = decodeURIComponent(
      atob(paddedBase64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );

    const decoded = JSON.parse(jsonPayload);
    
    if (decoded.user_id && decoded.email) {
      return {
        user_id: decoded.user_id,
        email: decoded.email,
      };
    }
    
    return null;
  } catch (error) {
    console.error('Failed to decode token:', error);
    return null;
  }
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [authState, setAuthState] = useState<AuthState>({
    token: null,
    user_id: null,
    email: null,
    isAuthenticated: false,
    isLoading: true, // Start as loading
  });

  // Load token from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    if (storedToken) {
      const decoded = decodeToken(storedToken);
      if (decoded) {
        setAuthState({
          token: storedToken,
          user_id: decoded.user_id,
          email: decoded.email,
          isAuthenticated: true,
          isLoading: false,
        });
      } else {
        // Invalid token, clear it
        localStorage.removeItem('auth_token');
        setAuthState(prev => ({ ...prev, isLoading: false }));
      }
    } else {
      setAuthState(prev => ({ ...prev, isLoading: false }));
    }
  }, []);

  const login = (token: string) => {
    const decoded = decodeToken(token);
    if (decoded) {
      localStorage.setItem('auth_token', token);
      setAuthState({
        token,
        user_id: decoded.user_id,
        email: decoded.email,
        isAuthenticated: true,
        isLoading: false,
      });
    } else {
      throw new Error('Invalid token format');
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setAuthState({
      token: null,
      user_id: null,
      email: null,
      isAuthenticated: false,
      isLoading: false,
    });
  };

  const register = () => {
    // Register function is a placeholder for now
    // The actual registration happens via API calls in the Register component
    // This function exists to match the interface but doesn't need implementation
  };

  return (
    <AuthContext.Provider
      value={{
        ...authState,
        login,
        logout,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
