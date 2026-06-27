export interface ErrorBannerProps {
  /** The error message to display to the user. */
  message: string;
  /** Optional retry callback. When provided, a "Try Again" button is rendered. */
  onRetry?: () => void;
}

/**
 * Displays an accessible error banner with an optional retry action.
 *
 * Uses `role="alert"` so screen readers announce the error immediately.
 * The retry button is only shown for recoverable errors (network failures, 5xx).
 */
export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      style={{
        padding: '1rem 1.25rem',
        borderRadius: '0.5rem',
        backgroundColor: '#fef2f2',
        border: '1px solid #fca5a5',
        color: '#991b1b',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        flexWrap: 'wrap',
      }}
    >
      <span style={{ flex: 1 }}>{message}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            padding: '0.5rem 1rem',
            borderRadius: '0.375rem',
            backgroundColor: '#991b1b',
            color: '#ffffff',
            border: 'none',
            cursor: 'pointer',
            fontWeight: 500,
          }}
        >
          Try Again
        </button>
      )}
    </div>
  );
}
