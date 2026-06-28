import { useState, useEffect, FormEvent } from 'react';
import { savePersonalBest, getPersonalBests, PersonalBest } from '../api/planService';
import './PersonalBestManager.css';

/**
 * Personal Best management component.
 * Allows manual PB entry and displays all PBs (manual + derived).
 */
export function PersonalBestManager() {
  const [pbs, setPbs] = useState<PersonalBest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [event, setEvent] = useState('');
  const [timeInput, setTimeInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const loadPBs = async () => {
    try {
      const data = await getPersonalBests();
      setPbs(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load personal bests.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPBs();
  }, []);

  /**
   * Parse time input in "M:SS", "M:SS.f", or raw seconds format.
   */
  const parseTime = (input: string): number | null => {
    const trimmed = input.trim();

    // M:SS or M:SS.f format
    const timeMatch = trimmed.match(/^(\d+):(\d{1,2}(?:\.\d+)?)$/);
    if (timeMatch) {
      const minutes = parseInt(timeMatch[1], 10);
      const seconds = parseFloat(timeMatch[2]);
      return minutes * 60 + seconds;
    }

    // Raw seconds
    const num = parseFloat(trimmed);
    if (!isNaN(num) && num > 0) {
      return num;
    }

    return null;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaveError(null);

    const timeSeconds = parseTime(timeInput);
    if (timeSeconds === null) {
      setSaveError('Enter time as M:SS (e.g., 1:05) or seconds (e.g., 65).');
      return;
    }

    setSaving(true);
    try {
      await savePersonalBest(event, timeSeconds);
      setEvent('');
      setTimeInput('');
      await loadPBs();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save personal best.';
      setSaveError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="pb-manager">
      <h1 className="pb-manager__heading">Personal Bests</h1>

      <div className="pb-manager__form-card">
        <h2 className="pb-manager__form-title">Add Personal Best</h2>
        <form className="pb-manager__form" onSubmit={handleSubmit}>
          <div className="pb-manager__field">
            <label className="pb-manager__label" htmlFor="pb-event">
              Event
            </label>
            <input
              id="pb-event"
              className="pb-manager__input"
              type="text"
              value={event}
              onChange={(e) => setEvent(e.target.value)}
              placeholder="e.g., 100m Freestyle"
              required
            />
          </div>

          <div className="pb-manager__field">
            <label className="pb-manager__label" htmlFor="pb-time">
              Time
            </label>
            <input
              id="pb-time"
              className="pb-manager__input"
              type="text"
              value={timeInput}
              onChange={(e) => setTimeInput(e.target.value)}
              placeholder="e.g., 1:05 or 65"
              required
            />
          </div>

          {saveError && (
            <p className="pb-manager__error" role="alert">
              {saveError}
            </p>
          )}

          <button
            className="pb-manager__submit"
            type="submit"
            disabled={saving}
          >
            {saving ? 'Saving…' : 'Save Personal Best'}
          </button>
        </form>
      </div>

      <section className="pb-manager__list-section" aria-label="Personal bests list">
        <h2 className="pb-manager__list-title">Your Personal Bests</h2>

        {loading ? (
          <p className="pb-manager__loading">Loading…</p>
        ) : error ? (
          <p className="pb-manager__error" role="alert">{error}</p>
        ) : pbs.length === 0 ? (
          <p className="pb-manager__empty">
            No personal bests recorded yet. Add one above or swim sessions to get derived PBs.
          </p>
        ) : (
          <div className="pb-manager__list">
            {pbs.map((pb) => (
              <div key={pb.event} className="pb-manager__item">
                <div className="pb-manager__item-main">
                  <span className="pb-manager__item-event">{pb.event}</span>
                  <span className="pb-manager__item-time">
                    {formatPBTime(pb.time_seconds)}
                  </span>
                </div>
                <div className="pb-manager__item-meta">
                  <SourceBadge source={pb.source} />
                  <time className="pb-manager__item-date" dateTime={pb.updated_at}>
                    {new Date(pb.updated_at).toLocaleDateString()}
                  </time>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function SourceBadge({ source }: { source: PersonalBest['source'] }) {
  const className = source === 'manual'
    ? 'pb-manager__source--manual'
    : 'pb-manager__source--derived';

  return (
    <span className={`pb-manager__source ${className}`}>
      {source}
    </span>
  );
}

function formatPBTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins > 0) {
    return `${mins}:${secs.toFixed(1).padStart(4, '0')}`;
  }
  return `${secs.toFixed(1)}s`;
}
