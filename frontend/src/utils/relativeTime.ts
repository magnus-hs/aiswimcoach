/**
 * Formats an ISO 8601 timestamp as a human-readable relative time string.
 *
 * Thresholds:
 * - < 60 seconds → "just now"
 * - < 3600 seconds → "N minutes ago" / "1 minute ago"
 * - < 86400 seconds → "N hours ago" / "1 hour ago"
 * - ≥ 86400 seconds → "N days ago" / "1 day ago"
 */
export function formatRelativeTime(timestamp: string): string {
  const then = new Date(timestamp).getTime();
  const now = Date.now();
  const diffSeconds = Math.floor((now - then) / 1000);

  if (diffSeconds < 60) {
    return 'just now';
  }

  if (diffSeconds < 3600) {
    const minutes = Math.floor(diffSeconds / 60);
    return minutes === 1 ? '1 minute ago' : `${minutes} minutes ago`;
  }

  if (diffSeconds < 86400) {
    const hours = Math.floor(diffSeconds / 3600);
    return hours === 1 ? '1 hour ago' : `${hours} hours ago`;
  }

  const days = Math.floor(diffSeconds / 86400);
  return days === 1 ? '1 day ago' : `${days} days ago`;
}
