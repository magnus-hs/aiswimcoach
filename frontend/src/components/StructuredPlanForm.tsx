import { useState, FormEvent } from 'react';
import { generateStructuredPlan, StructuredPlan } from '../api/planService';
import { ApiError } from '../types';
import { UpgradePrompt } from './UpgradePrompt';
import './StructuredPlanForm.css';

export interface StructuredPlanFormProps {
  onPlanGenerated: (plan: StructuredPlan) => void;
}

/**
 * Form for generating a multi-week structured training plan.
 * Collects event, target time, duration, and sessions per week.
 */
export function StructuredPlanForm({ onPlanGenerated }: StructuredPlanFormProps) {
  const [event, setEvent] = useState('');
  const [targetTime, setTargetTime] = useState('');
  const [weeks, setWeeks] = useState(8);
  const [sessionsPerWeek, setSessionsPerWeek] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showUpgrade, setShowUpgrade] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const plan = await generateStructuredPlan({
        event,
        target_time: targetTime,
        weeks,
        sessions_per_week: sessionsPerWeek,
      });
      onPlanGenerated(plan);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 403 || err.status === 429)) {
        const msg = err.serverMessage.toLowerCase();
        if (msg.includes('upgrade') || msg.includes('premium')) {
          setShowUpgrade(true);
          return;
        }
      }
      const message =
        err instanceof Error ? err.message : 'Failed to generate plan.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  if (showUpgrade) {
    return <UpgradePrompt message="Training plan generation is a premium feature. Subscribe for £3/month to unlock personalised multi-week training plans." />;
  }

  return (
    <form className="structured-plan-form" onSubmit={handleSubmit}>
      <h2 className="structured-plan-form__title">Generate Structured Plan</h2>

      <div className="structured-plan-form__field">
        <label className="structured-plan-form__label" htmlFor="plan-event">
          Event
        </label>
        <input
          id="plan-event"
          className="structured-plan-form__input"
          type="text"
          value={event}
          onChange={(e) => setEvent(e.target.value)}
          placeholder="e.g., 100m Freestyle"
          required
        />
      </div>

      <div className="structured-plan-form__field">
        <label className="structured-plan-form__label" htmlFor="plan-target-time">
          Target Time
        </label>
        <input
          id="plan-target-time"
          className="structured-plan-form__input"
          type="text"
          value={targetTime}
          onChange={(e) => setTargetTime(e.target.value)}
          placeholder="e.g., 1:05"
          required
        />
      </div>

      <div className="structured-plan-form__row">
        <div className="structured-plan-form__field">
          <label className="structured-plan-form__label" htmlFor="plan-weeks">
            Duration (weeks)
          </label>
          <input
            id="plan-weeks"
            className="structured-plan-form__input"
            type="number"
            min={4}
            max={12}
            value={weeks}
            onChange={(e) => setWeeks(Number(e.target.value))}
            required
          />
        </div>

        <div className="structured-plan-form__field">
          <label className="structured-plan-form__label" htmlFor="plan-sessions">
            Sessions / Week
          </label>
          <input
            id="plan-sessions"
            className="structured-plan-form__input"
            type="number"
            min={3}
            max={5}
            value={sessionsPerWeek}
            onChange={(e) => setSessionsPerWeek(Number(e.target.value))}
            required
          />
        </div>
      </div>

      {error && (
        <p className="structured-plan-form__error" role="alert">
          {error}
        </p>
      )}

      <button
        className="structured-plan-form__submit"
        type="submit"
        disabled={loading}
      >
        {loading ? 'Generating…' : 'Generate Plan'}
      </button>

      {loading && (
        <p className="structured-plan-form__loading" aria-live="polite">
          Generating your multi-week training plan. This may take a moment…
        </p>
      )}
    </form>
  );
}
