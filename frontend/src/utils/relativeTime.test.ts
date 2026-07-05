// Feature: ai-coach-context, Property 9: Relative timestamp formatting
// **Validates: Requirements 4.7**

import { describe, it, expect, vi, afterEach } from 'vitest';
import * as fc from 'fast-check';
import { formatRelativeTime } from './relativeTime';

describe('Property 9: Relative timestamp formatting', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns "just now" when difference < 60 seconds', () => {
    fc.assert(
      fc.property(
        // Generate a "now" timestamp (any recent time) and a diff in [0, 59] seconds
        fc.integer({ min: 1_000_000_000_000, max: 2_000_000_000_000 }),
        fc.integer({ min: 0, max: 59 }),
        (nowMs, diffSeconds) => {
          vi.spyOn(Date, 'now').mockReturnValue(nowMs);
          const timestamp = new Date(nowMs - diffSeconds * 1000).toISOString();
          const result = formatRelativeTime(timestamp);
          expect(result).toBe('just now');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('returns "N minutes ago" when difference is [60, 3599] seconds', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1_000_000_000_000, max: 2_000_000_000_000 }),
        fc.integer({ min: 60, max: 3599 }),
        (nowMs, diffSeconds) => {
          vi.spyOn(Date, 'now').mockReturnValue(nowMs);
          const timestamp = new Date(nowMs - diffSeconds * 1000).toISOString();
          const result = formatRelativeTime(timestamp);

          const expectedMinutes = Math.floor(diffSeconds / 60);
          const expected = expectedMinutes === 1
            ? '1 minute ago'
            : `${expectedMinutes} minutes ago`;
          expect(result).toBe(expected);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('returns "N hours ago" when difference is [3600, 86399] seconds', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1_000_000_000_000, max: 2_000_000_000_000 }),
        fc.integer({ min: 3600, max: 86399 }),
        (nowMs, diffSeconds) => {
          vi.spyOn(Date, 'now').mockReturnValue(nowMs);
          const timestamp = new Date(nowMs - diffSeconds * 1000).toISOString();
          const result = formatRelativeTime(timestamp);

          const expectedHours = Math.floor(diffSeconds / 3600);
          const expected = expectedHours === 1
            ? '1 hour ago'
            : `${expectedHours} hours ago`;
          expect(result).toBe(expected);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('returns "N days ago" when difference is >= 86400 seconds', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1_000_000_000_000, max: 2_000_000_000_000 }),
        fc.integer({ min: 86400, max: 86400 * 365 }),
        (nowMs, diffSeconds) => {
          vi.spyOn(Date, 'now').mockReturnValue(nowMs);
          const timestamp = new Date(nowMs - diffSeconds * 1000).toISOString();
          const result = formatRelativeTime(timestamp);

          const expectedDays = Math.floor(diffSeconds / 86400);
          const expected = expectedDays === 1
            ? '1 day ago'
            : `${expectedDays} days ago`;
          expect(result).toBe(expected);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('always returns one of the valid format patterns for any valid timestamp <= now', () => {
    const validPattern = /^(just now|\d+ minutes? ago|\d+ hours? ago|\d+ days? ago)$/;

    fc.assert(
      fc.property(
        fc.integer({ min: 1_000_000_000_000, max: 2_000_000_000_000 }),
        fc.integer({ min: 0, max: 86400 * 3650 }), // up to ~10 years
        (nowMs, diffSeconds) => {
          vi.spyOn(Date, 'now').mockReturnValue(nowMs);
          const timestamp = new Date(nowMs - diffSeconds * 1000).toISOString();
          const result = formatRelativeTime(timestamp);
          expect(result).toMatch(validPattern);
        }
      ),
      { numRuns: 100 }
    );
  });
});
