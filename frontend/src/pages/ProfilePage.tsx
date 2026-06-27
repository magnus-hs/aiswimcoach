import { useState, useEffect, useCallback, FormEvent, ChangeEvent } from 'react';
import { saveProfile, getProfile, uploadProfilePicture, UserProfile } from '../api/profileService';
import { ApiError } from '../types';

/**
 * ProfilePage - User profile management with form and picture upload.
 * 
 * Features:
 * - Profile form with age, nationality, locality, ability_level
 * - Client-side validation (age 10-100, ability_level required)
 * - Profile picture upload with preview
 * - Load existing profile on mount
 * - Success/error message display
 * 
 * Validates: Requirements 4.1-4.9, 23.1-23.4, 23.12
 */
export function ProfilePage() {
  // Form state
  const [age, setAge] = useState<string>('');
  const [nationality, setNationality] = useState<string>('');
  const [locality, setLocality] = useState<string>('');
  const [abilityLevel, setAbilityLevel] = useState<string>('');

  // Profile picture state
  const [profilePicture, setProfilePicture] = useState<File | null>(null);
  const [picturePreview, setPicturePreview] = useState<string>('');

  // UI state
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingProfile, setLoadingProfile] = useState<boolean>(true);
  const [successMessage, setSuccessMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [ageError, setAgeError] = useState<string>('');

  // Load existing profile on mount
  useEffect(() => {
    async function loadProfile() {
      try {
        const profile = await getProfile();
        if (profile) {
          setAge(profile.age.toString());
          setNationality(profile.nationality || '');
          setLocality(profile.locality || '');
          setAbilityLevel(profile.ability_level);
        }
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status !== 404) {
          setErrorMessage(err.serverMessage);
        }
        // 404 means no profile yet, which is fine
      } finally {
        setLoadingProfile(false);
      }
    }

    loadProfile();
  }, []);

  // Validate age on change
  const handleAgeChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setAge(value);
    setAgeError('');

    if (value === '') {
      return;
    }

    const ageNum = parseInt(value, 10);
    if (isNaN(ageNum) || ageNum < 10 || ageNum > 100) {
      setAgeError('Age must be between 10 and 100');
    }
  }, []);

  // Handle profile picture selection
  const handlePictureChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setProfilePicture(file);
      
      // Create preview URL
      const reader = new FileReader();
      reader.onloadend = () => {
        setPicturePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  }, []);

  // Check if form is valid
  const isFormValid = useCallback(() => {
    if (age === '' || ageError !== '' || abilityLevel === '') {
      return false;
    }
    const ageNum = parseInt(age, 10);
    return !isNaN(ageNum) && ageNum >= 10 && ageNum <= 100;
  }, [age, ageError, abilityLevel]);

  // Handle form submission
  const handleSubmit = useCallback(async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    setSuccessMessage('');
    setErrorMessage('');

    if (!isFormValid()) {
      setErrorMessage('Please fill in all required fields correctly');
      return;
    }

    setLoading(true);

    try {
      const profile: UserProfile = {
        age: parseInt(age, 10),
        nationality: nationality.trim(),
        locality: locality.trim(),
        ability_level: abilityLevel as 'beginner' | 'intermediate' | 'advanced' | 'elite',
      };

      // Save profile
      await saveProfile(profile);

      // Upload profile picture if selected
      if (profilePicture) {
        await uploadProfilePicture(profilePicture);
      }

      setSuccessMessage('Profile saved successfully!');
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMessage(err.serverMessage);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to save profile');
      }
    } finally {
      setLoading(false);
    }
  }, [age, nationality, locality, abilityLevel, profilePicture, isFormValid]);

  if (loadingProfile) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <p style={{ color: '#64748b' }}>Loading profile...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card" style={{ maxWidth: '540px' }}>
        <div className="auth-card__header">
          <span className="auth-card__icon" role="img" aria-label="Profile">
            👤
          </span>
          <h1 className="auth-card__title">Your Profile</h1>
          <p className="auth-card__subtitle">
            Complete your profile to enable personalized coaching and heart rate zone analysis
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {successMessage && (
            <div style={{
              background: '#f0fdf4',
              border: '1px solid #86efac',
              borderRadius: '8px',
              padding: '0.875rem 1rem',
              color: '#166534',
              fontSize: '0.875rem',
            }}>
              {successMessage}
            </div>
          )}

          {errorMessage && (
            <div className="auth-form__error">
              {errorMessage}
            </div>
          )}

          {/* Profile Picture Upload */}
          <div className="auth-form__field">
            <label className="auth-form__label">Profile Picture</label>
            <input
              type="file"
              accept="image/jpeg,image/png,image/gif"
              onChange={handlePictureChange}
              disabled={loading}
              style={{
                padding: '0.75rem 1rem',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '0.875rem',
              }}
            />
            {picturePreview && (
              <div style={{ marginTop: '0.5rem' }}>
                <img
                  src={picturePreview}
                  alt="Profile preview"
                  style={{
                    width: '120px',
                    height: '120px',
                    objectFit: 'cover',
                    borderRadius: '50%',
                    border: '3px solid #3b82f6',
                  }}
                />
              </div>
            )}
          </div>

          {/* Age Field */}
          <div className="auth-form__field">
            <label htmlFor="age" className="auth-form__label">
              Age <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <input
              id="age"
              type="number"
              min="10"
              max="100"
              value={age}
              onChange={handleAgeChange}
              disabled={loading}
              className="auth-form__input"
              placeholder="Enter your age (10-100)"
              required
            />
            {ageError && (
              <div style={{
                fontSize: '0.8125rem',
                color: '#ef4444',
                marginTop: '-0.25rem',
              }}>
                {ageError}
              </div>
            )}
          </div>

          {/* Nationality Field */}
          <div className="auth-form__field">
            <label htmlFor="nationality" className="auth-form__label">
              Nationality
            </label>
            <input
              id="nationality"
              type="text"
              maxLength={100}
              value={nationality}
              onChange={(e) => setNationality(e.target.value)}
              disabled={loading}
              className="auth-form__input"
              placeholder="e.g., American, British, German"
            />
          </div>

          {/* Locality Field */}
          <div className="auth-form__field">
            <label htmlFor="locality" className="auth-form__label">
              Locality
            </label>
            <input
              id="locality"
              type="text"
              maxLength={100}
              value={locality}
              onChange={(e) => setLocality(e.target.value)}
              disabled={loading}
              className="auth-form__input"
              placeholder="e.g., California, London, Bavaria"
            />
          </div>

          {/* Ability Level Field */}
          <div className="auth-form__field">
            <label htmlFor="ability-level" className="auth-form__label">
              Ability Level <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <select
              id="ability-level"
              value={abilityLevel}
              onChange={(e) => setAbilityLevel(e.target.value)}
              disabled={loading}
              className="auth-form__input"
              required
              style={{
                cursor: 'pointer',
              }}
            >
              <option value="">Select your ability level</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
              <option value="elite">Elite</option>
            </select>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="auth-form__submit"
            disabled={loading || !isFormValid()}
          >
            {loading ? 'Saving...' : 'Save Profile'}
          </button>
        </form>
      </div>
    </div>
  );
}
