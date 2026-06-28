import { describe, it, expect, vi, afterEach } from 'vitest';
import { computeStreak } from './computeStreak';

describe('computeStreak', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns 0 for empty array', () => {
    expect(computeStreak([])).toBe(0);
  });

  it('returns 0 when today has no session', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-06-15T12:00:00'));

    // Only yesterday has a session
    expect(computeStreak(['2024-06-14'])).toBe(0);
  });

  it('returns 1 when only today has a session', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-06-15T12:00:00'));

    expect(computeStreak(['2024-06-15'])).toBe(1);
  });

  it('returns correct streak for consecutive days ending today', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-06-15T12:00:00'));

    expect(computeStreak(['2024-06-15', '2024-06-14', '2024-06-13'])).toBe(3);
  });

  it('stops counting at a gap', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-06-15T12:00:00'));

    // Today, yesterday, skip a day, then another session
    expect(computeStreak(['2024-06-15', '2024-06-14', '2024-06-12'])).toBe(2);
  });

  it('handles duplicate dates on the same day', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-06-15T12:00:00'));

    // Multiple sessions on the same day should count as one day
    expect(computeStreak([
      '2024-06-15T08:00:00',
      '2024-06-15T16:00:00',
      '2024-06-14T10:00:00',
    ])).toBe(2);
  });

  it('handles ISO 8601 datetime strings with timezone info', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-06-15T12:00:00'));

    expect(computeStreak([
      '2024-06-15T09:30:00.000Z',
      '2024-06-14T14:00:00.000Z',
      '2024-06-13T07:45:00.000Z',
    ])).toBe(3);
  });

  it('handles unordered dates', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-06-15T12:00:00'));

    // Dates not in order should still compute correctly
    expect(computeStreak(['2024-06-13', '2024-06-15', '2024-06-14'])).toBe(3);
  });
});
