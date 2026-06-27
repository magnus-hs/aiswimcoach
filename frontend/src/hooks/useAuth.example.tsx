/**
 * Example usage of the useAuth hook
 * 
 * This file demonstrates how to use the authentication context
 * in different components throughout the application.
 */

import React from 'react';
import { AuthProvider, useAuth } from './useAuth';

// 1. Wrap your app with AuthProvider at the root level
function App() {
  return (
    <AuthProvider>
      <YourAppComponents />
    </AuthProvider>
  );
}

// 2. Access authentication state in any component
function UserProfile() {
  const { email, user_id, isAuthenticated } = useAuth();
  
  if (!isAuthenticated) {
    return <div>Please log in</div>;
  }
  
  return (
    <div>
      <h1>Profile</h1>
      <p>Email: {email}</p>
      <p>User ID: {user_id}</p>
    </div>
  );
}

// 3. Use login function after successful authentication
function LoginComponent() {
  const { login } = useAuth();
  
  const handleLogin = async (email: string, password: string) => {
    try {
      // Call your auth API
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      
      const data = await response.json();
      
      // Store token and decode user info
      login(data.token);
      
      // User is now authenticated, redirect to protected route
      window.location.href = '/upload';
    } catch (error) {
      console.error('Login failed:', error);
    }
  };
  
  return <div>Login form here</div>;
}

// 4. Use logout function to clear authentication
function LogoutButton() {
  const { logout } = useAuth();
  
  const handleLogout = () => {
    logout();
    // User is now logged out, redirect to login page
    window.location.href = '/login';
  };
  
  return <button onClick={handleLogout}>Logout</button>;
}

// 5. Create protected routes that check authentication
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  
  if (!isAuthenticated) {
    // Redirect to login
    window.location.href = '/login';
    return null;
  }
  
  return <>{children}</>;
}

// 6. Use token for authenticated API requests
function UploadComponent() {
  const { token } = useAuth();
  
  const uploadFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/upload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });
    
    return response.json();
  };
  
  return <div>Upload form here</div>;
}

// Dummy component for example
function YourAppComponents() {
  return <div>Your app</div>;
}
