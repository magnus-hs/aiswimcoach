/**
 * Compute consecutive-day training streak from session dates.
 * A streak counts backward from today, incrementing for each
 * consecutive calendar day that has at least one session.
 * If today has no session, returns 0.
 */
export function computeStreak(sessionDates: string[]): number {
  if (sessionDates.length === 0) return 0;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const uniqueDays = new Set(
    sessionDates.map(d => {
      const date = new Date(d);
      date.setHours(0, 0, 0, 0);
      return date.getTime();
    })
  );

  let streak = 0;
  let checkDate = new Date(today);

  while (uniqueDays.has(checkDate.getTime())) {
    streak++;
    checkDate.setDate(checkDate.getDate() - 1);
  }

  return streak;
}
