import { useState, useEffect, FormEvent } from 'react';
import { savePersonalBest, getPersonalBests, PersonalBest } from '../api/planService';
import { STROKES, DISTANCES, StrokeType, DistanceOption, buildEventName, validateTimeInput, validateCustomDistance } from '../utils/pbValidation';
import { groupPersonalBests, formatTimeDiff } from '../utils/pbGrouping';
import './PersonalBestManager.css';

/**
 * Personal Best management component.
 * Allows manual PB entry and displays all PBs (manual + derived).
 */
export function PersonalBestManager() {
  const [pbs, setPbs] = useState<PersonalBest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stroke, setStroke] = useState<StrokeType | ''>('');
  const [distance, setDistance] = useState<DistanceOption | ''>('');
  const [customDistance, setCustomDistance] = useState('');
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

  const isFormValid =
    stroke !== '' &&
    distance !== '' &&
    timeInput.trim() !== '' &&
    (distance !== 'Custom' || customDistance.trim() !== '');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaveError(null);

    // Validate time
    const timeResult = validateTimeInput(timeInput);
    if (!timeResult.valid) {
      setSaveError(timeResult.error || 'Enter time as M:SS (e.g., 1:05)');
      return;
    }

    // Validate custom distance if applicable
    if (distance === 'Custom') {
      const distResult = validateCustomDistance(customDistance);
      if (!distResult.valid) {
        setSaveError(distResult.error || 'Distance must be between 25 and 5000 meters');
        return;
      }
    }

    const eventName = buildEventName(stroke as StrokeType, distance as DistanceOption, customDistance);
    const timeSeconds = timeResult.seconds!;

    setSaving(true);
    try {
      await savePersonalBest(eventName, timeSeconds);
      setStroke('');
      setDistance('');
      setCustomDistance('');
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

      <section className="pb-manager__list-section" aria-label="Personal bests list">
        {loading ? (
          <p className="pb-manager__loading">Loading…</p>
        ) : error ? (
          <p className="pb-manager__error" role="alert">{error}</p>
        ) : pbs.length === 0 ? (
          <p className="pb-manager__empty">
            No personal bests recorded yet. Add one below or upload swim sessions to get derived PBs.
          </p>
        ) : (
          <div className="pb-manager__groups">
            {groupPersonalBests(pbs).map((group) => (
              <div key={group.stroke} className="pb-manager__group">
                <h2 className="pb-manager__group-heading">{group.stroke}</h2>
                <table className="pb-manager__table">
                  <thead>
                    <tr>
                      <th className="pb-manager__th">Distance</th>
                      <th className="pb-manager__th">Entered</th>
                      <th className="pb-manager__th">Derived</th>
                      <th className="pb-manager__th">Diff</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.events.map((entry) => (
                      <tr key={`${group.stroke}-${entry.event}`} className="pb-manager__row">
                        <td className="pb-manager__td pb-manager__td--distance">{entry.distance}m</td>
                        <td className="pb-manager__td">
                          {entry.manual ? formatPBTime(entry.manual.time_seconds) : '—'}
                        </td>
                        <td className="pb-manager__td">
                          {entry.derived ? formatPBTime(entry.derived.time_seconds) : '—'}
                        </td>
                        <td className="pb-manager__td">
                          {entry.manual && entry.derived ? (
                            <span className={`pb-manager__diff pb-manager__diff--${formatTimeDiff(entry.manual.time_seconds, entry.derived.time_seconds).label}`}>
                              {formatTimeDiff(entry.manual.time_seconds, entry.derived.time_seconds).diff}s {formatTimeDiff(entry.manual.time_seconds, entry.derived.time_seconds).label}
                            </span>
                          ) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="pb-manager__form-card">
        <h2 className="pb-manager__form-title">Add Personal Best</h2>
        <form className="pb-manager__form" onSubmit={handleSubmit}>
          <div className="pb-manager__field">
            <label className="pb-manager__label" htmlFor="pb-stroke">
              Stroke
            </label>
            <select
              id="pb-stroke"
              className="pb-manager__select"
              value={stroke}
              onChange={(e) => setStroke(e.target.value as StrokeType | '')}
              required
            >
              <option value="">Select stroke</option>
              {STROKES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="pb-manager__field">
            <label className="pb-manager__label" htmlFor="pb-distance">
              Distance
            </label>
            <select
              id="pb-distance"
              className="pb-manager__select"
              value={distance}
              onChange={(e) => setDistance(e.target.value as DistanceOption | '')}
              required
            >
              <option value="">Select distance</option>
              {DISTANCES.map((d) => (
                <option key={d} value={d}>{d === 'Custom' ? 'Custom' : `${d}m`}</option>
              ))}
            </select>
          </div>

          {distance === 'Custom' && (
            <div className="pb-manager__field">
              <label className="pb-manager__label" htmlFor="pb-custom-distance">
                Custom Distance (meters)
              </label>
              <input
                id="pb-custom-distance"
                className="pb-manager__input"
                type="number"
                min={25}
                max={5000}
                step={1}
                value={customDistance}
                onChange={(e) => setCustomDistance(e.target.value)}
                placeholder="25–5000"
                required
              />
            </div>
          )}

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
              placeholder="M:SS (e.g., 1:05)"
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
            disabled={saving || !isFormValid}
          >
            {saving ? 'Saving…' : 'Save Personal Best'}
          </button>
        </form>
      </div>
    </div>
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
