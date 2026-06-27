import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Header } from './Header';
import { AuthProvider } from '../hooks/useAuth';

// Mock environment variable
vi.mock('import.meta', () => ({
  env: {
    VITE_API_ENDPOINT: 'http://localhost:3000',
  },
}));

// Mock global fetch
(globalThis as any).fetch = vi.fn();

const renderHeader = (isAuthenticated = true) => {
  if (isAuthenticated) {
    localStorage.setItem('auth_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLWlkIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjk5OTk5OTk5OTl9.signature');
  } else {
    localStorage.removeItem('auth_token');
  }

  return render(
    <BrowserRouter>
      <AuthProvider>
        <Header />
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('Header Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders simple header on public routes when not authenticated', () => {
    renderHeader(false);
    expect(screen.getByText('AI Swim Coach')).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('renders full header with sidebar when authenticated', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ profile_picture_url: null }),
    });

    renderHeader(true);

    // Wait for component to mount and fetch
    await waitFor(() => {
      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    // Check navigation links
    expect(screen.getByText('Upload')).toBeInTheDocument();
    expect(screen.getByText('History')).toBeInTheDocument();
    expect(screen.getByText('Profile')).toBeInTheDocument();
    expect(screen.getByText('Logout')).toBeInTheDocument();

    // Check user email is displayed
    expect(screen.getByText('test@example.com')).toBeInTheDocument();
  });

  it('displays profile avatar placeholder when no profile picture', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ profile_picture_url: null }),
    });

    renderHeader(true);

    await waitFor(() => {
      expect(screen.getByLabelText('View profile')).toBeInTheDocument();
    });
  });

  it('fetches user info on mount', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ profile_picture_url: 'https://example.com/pic.jpg' }),
    });

    renderHeader(true);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/user'),
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            Authorization: expect.stringContaining('Bearer'),
          }),
        })
      );
    });
  });
});
