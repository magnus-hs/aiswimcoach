import { useState, useEffect, useRef, useCallback, FormEvent, ChangeEvent } from 'react';
import { saveProfile, getProfile, uploadProfilePicture, UserProfile } from '../api/profileService';
import { ApiError } from '../types';
import './ProfileModal.css';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  triggerRef: React.RefObject<HTMLElement>;
}

/**
 * ProfileModal — Accessible modal overlay for viewing/editing profile.
 *
 * Features:
 * - Focus trap (Tab/Shift+Tab cycling within modal)
 * - Dismiss via Escape key, backdrop click, or close button
 * - Returns focus to trigger element on close
 * - ARIA: role="dialog", aria-modal="true", aria-label
 *
 * Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
 */
export function ProfileModal({ isOpen, onClose, triggerRef }: ProfileModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

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
  const [loadingProfile, setLoadingProfile] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [ageError, setAgeError] = useState<string>('');

  // Load profile when modal opens
  useEffect(() => {
    if (!isOpen) return;

    setLoadingProfile(true);
    setSuccessMessage('');
    setErrorMessage('');

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
      } finally {
        setLoadingProfile(false);
      }
    }

    loadProfile();
  }, [isOpen]);

  // Focus trap and keyboard handling
  useEffect(() => {
    if (!isOpen) return;

    const modalEl = modalRef.current;
    if (!modalEl) return;

    const getFocusableElements = () => {
      return modalEl.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
    };

    // Focus the first focusable element when modal opens
    const focusableElements = getFocusableElements();
    const firstFocusable = focusableElements[0];
    firstFocusable?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        triggerRef.current?.focus();
        return;
      }

      if (e.key === 'Tab') {
        const currentFocusable = getFocusableElements();
        if (currentFocusable.length === 0) return;

        const first = currentFocusable[0];
        const last = currentFocusable[currentFocusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, triggerRef]);

  const handleClose = useCallback(() => {
    onClose();
    triggerRef.current?.focus();
  }, [onClose, triggerRef]);

  const handleBackdropClick = useCallback(() => {
    handleClose();
  }, [handleClose]);

  const handleModalClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
  }, []);

  // Validate age on change
  const handleAgeChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setAge(value);
    setAgeError('');

    if (value === '') return;

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

      await saveProfile(profile);

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

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div
        ref={modalRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Profile settings"
        onClick={handleModalClick}
      >
        <div className="modal__header">
          <h2 className="modal__title">Your Profile</h2>
          <button
            className="modal__close"
            onClick={handleClose}
            aria-label="Close"
            type="button"
          >
            ×
          </button>
        </div>

        {loadingProfile ? (
          <div className="modal__loading">Loading profile...</div>
        ) : (
          <form className="modal__form" onSubmit={handleSubmit}>
            {successMessage && (
              <div className="modal__message--success">{successMessage}</div>
            )}

            {errorMessage && (
              <div className="modal__message--error">{errorMessage}</div>
            )}

            {/* Profile Picture */}
            <div className="modal__field">
              <label className="modal__label">Profile Picture</label>
              <input
                type="file"
                accept="image/jpeg,image/png,image/gif"
                onChange={handlePictureChange}
                disabled={loading}
                className="modal__picture-input"
              />
              {picturePreview && (
                <div className="modal__picture-preview">
                  <img src={picturePreview} alt="Profile preview" />
                </div>
              )}
            </div>

            {/* Age */}
            <div className="modal__field">
              <label htmlFor="modal-age" className="modal__label modal__label--required">
                Age
              </label>
              <input
                id="modal-age"
                type="number"
                min="10"
                max="100"
                value={age}
                onChange={handleAgeChange}
                disabled={loading}
                className="modal__input"
                placeholder="Enter your age (10-100)"
                required
              />
              {ageError && <div className="modal__field-error">{ageError}</div>}
            </div>

            {/* Nationality */}
            <div className="modal__field">
              <label htmlFor="modal-nationality" className="modal__label">
                Nationality
              </label>
              <input
                id="modal-nationality"
                type="text"
                maxLength={100}
                value={nationality}
                onChange={(e) => setNationality(e.target.value)}
                disabled={loading}
                className="modal__input"
                placeholder="e.g., American, British, German"
              />
            </div>

            {/* Locality */}
            <div className="modal__field">
              <label htmlFor="modal-locality" className="modal__label">
                Locality
              </label>
              <input
                id="modal-locality"
                type="text"
                maxLength={100}
                value={locality}
                onChange={(e) => setLocality(e.target.value)}
                disabled={loading}
                className="modal__input"
                placeholder="e.g., California, London, Bavaria"
              />
            </div>

            {/* Ability Level */}
            <div className="modal__field">
              <label htmlFor="modal-ability-level" className="modal__label modal__label--required">
                Ability Level
              </label>
              <select
                id="modal-ability-level"
                value={abilityLevel}
                onChange={(e) => setAbilityLevel(e.target.value)}
                disabled={loading}
                className="modal__select"
                required
              >
                <option value="">Select your ability level</option>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
                <option value="elite">Elite</option>
              </select>
            </div>

            {/* Submit */}
            <button
              type="submit"
              className="modal__submit"
              disabled={loading || !isFormValid()}
            >
              {loading ? 'Saving...' : 'Save Profile'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
