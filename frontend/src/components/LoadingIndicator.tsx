/**
 * Simple loading spinner displayed while an upload is in progress.
 *
 * Validates: Requirements 1.5
 */
export function LoadingIndicator() {
  return (
    <div
      role="status"
      aria-label="Upload in progress"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '0.75rem',
        padding: '2rem',
      }}
    >
      <div
        className="loading-spinner"
        style={{
          width: '2.5rem',
          height: '2.5rem',
          border: '3px solid #e5e7eb',
          borderTopColor: '#2563eb',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      <p style={{ color: '#4b5563', margin: 0 }}>Analysing your swim data…</p>
    </div>
  );
}
