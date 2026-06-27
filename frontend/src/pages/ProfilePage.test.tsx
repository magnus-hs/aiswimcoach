import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { ProfilePage } from './ProfilePage';
import * as profileService from '../api/profileService';

// Mock the profile service
vi.mock('../api/profileService');

describe('ProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(() => 'mock-token'),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true,
    });
  });

  it('renders the profile form', async () => {
    vi.mocked(profileService.getProfile).mockResolvedValue(null);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText('Your Profile')).toBeInTheDocument();
    });

    // Check for form fields
    expect(screen.getByLabelText(/Age/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Nationality/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Locality/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Ability Level/)).toBeInTheDocument();
    expect(screen.getByText('Profile Picture')).toBeInTheDocument();
  });

  it('loads and displays existing profile data', async () => {
    const mockProfile: profileService.UserProfile = {
      age: 30,
      nationality: 'American',
      locality: 'California',
      ability_level: 'intermediate',
    };

    vi.mocked(profileService.getProfile).mockResolvedValue(mockProfile);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('30')).toBeInTheDocument();
      expect(screen.getByDisplayValue('American')).toBeInTheDocument();
      expect(screen.getByDisplayValue('California')).toBeInTheDocument();
    });

    // Check select value by finding the option
    const abilitySelect = screen.getByLabelText(/Ability Level/) as HTMLSelectElement;
    expect(abilitySelect.value).toBe('intermediate');
  });

  it('disables submit button when form is invalid', async () => {
    vi.mocked(profileService.getProfile).mockResolvedValue(null);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText('Your Profile')).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /Save Profile/i });
    expect(submitButton).toBeDisabled();
  });

  it('shows validation error when age is out of range', async () => {
    vi.mocked(profileService.getProfile).mockResolvedValue(null);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText('Your Profile')).toBeInTheDocument();
    });

    const ageInput = screen.getByLabelText(/Age/) as HTMLInputElement;
    
    // Trigger the onChange handler
    fireEvent.change(ageInput, { target: { value: '5' } });

    await waitFor(() => {
      expect(screen.getByText('Age must be between 10 and 100')).toBeInTheDocument();
    });
  });
});
