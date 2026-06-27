import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { AuthProvider, useAuth } from './useAuth';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('useAuth hook', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it('should start with unauthenticated state when no token in localStorage', () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
    expect(result.current.user_id).toBeNull();
    expect(result.current.email).toBeNull();
  });

  it('should load token from localStorage on mount and decode it', () => {
    // Create a valid JWT token with user_id and email in payload
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payload = btoa(
      JSON.stringify({
        user_id: 'test-user-123',
        email: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 3600,
      })
    );
    const signature = 'fake-signature';
    const token = `${header}.${payload}.${signature}`;

    localStorageMock.setItem('auth_token', token);

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.token).toBe(token);
    expect(result.current.user_id).toBe('test-user-123');
    expect(result.current.email).toBe('test@example.com');
  });

  it('should clear invalid token from localStorage on mount', () => {
    localStorageMock.setItem('auth_token', 'invalid-token');

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(localStorageMock.getItem('auth_token')).toBeNull();
  });

  it('should login successfully with valid token', () => {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payload = btoa(
      JSON.stringify({
        user_id: 'user-456',
        email: 'user@example.com',
      })
    );
    const signature = 'fake-signature';
    const token = `${header}.${payload}.${signature}`;

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    act(() => {
      result.current.login(token);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.token).toBe(token);
    expect(result.current.user_id).toBe('user-456');
    expect(result.current.email).toBe('user@example.com');
    expect(localStorageMock.getItem('auth_token')).toBe(token);
  });

  it('should throw error when login called with invalid token', () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    expect(() => {
      act(() => {
        result.current.login('invalid-token');
      });
    }).toThrow('Invalid token format');
  });

  it('should logout and clear localStorage', () => {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payload = btoa(
      JSON.stringify({
        user_id: 'user-789',
        email: 'logout@example.com',
      })
    );
    const signature = 'fake-signature';
    const token = `${header}.${payload}.${signature}`;

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    // First login
    act(() => {
      result.current.login(token);
    });

    expect(result.current.isAuthenticated).toBe(true);

    // Then logout
    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
    expect(result.current.user_id).toBeNull();
    expect(result.current.email).toBeNull();
    expect(localStorageMock.getItem('auth_token')).toBeNull();
  });

  it('should handle URL-safe base64 in JWT token', () => {
    // Create token with URL-safe base64 characters
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
    
    const payload = btoa(
      JSON.stringify({
        user_id: 'url-safe-user',
        email: 'urlsafe@example.com',
      })
    )
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');

    const signature = 'fake-signature';
    const token = `${header}.${payload}.${signature}`;

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    act(() => {
      result.current.login(token);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user_id).toBe('url-safe-user');
    expect(result.current.email).toBe('urlsafe@example.com');
  });

  it('should reject token missing user_id', () => {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payload = btoa(
      JSON.stringify({
        email: 'noid@example.com',
      })
    );
    const signature = 'fake-signature';
    const token = `${header}.${payload}.${signature}`;

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    expect(() => {
      act(() => {
        result.current.login(token);
      });
    }).toThrow('Invalid token format');
  });

  it('should reject token missing email', () => {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payload = btoa(
      JSON.stringify({
        user_id: 'user-no-email',
      })
    );
    const signature = 'fake-signature';
    const token = `${header}.${payload}.${signature}`;

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    expect(() => {
      act(() => {
        result.current.login(token);
      });
    }).toThrow('Invalid token format');
  });

  it('should reject token with wrong number of parts', () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    expect(() => {
      act(() => {
        result.current.login('header.payload');
      });
    }).toThrow('Invalid token format');

    expect(() => {
      act(() => {
        result.current.login('only-one-part');
      });
    }).toThrow('Invalid token format');
  });

  it('should provide register function (placeholder)', () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    // register() is a placeholder, should not throw
    expect(() => {
      act(() => {
        result.current.register();
      });
    }).not.toThrow();
  });

  it('should throw error when useAuth used outside AuthProvider', () => {
    // Suppress console.error for this test as React will log the error
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useAuth());
    }).toThrow('useAuth must be used within an AuthProvider');

    consoleSpy.mockRestore();
  });
});
