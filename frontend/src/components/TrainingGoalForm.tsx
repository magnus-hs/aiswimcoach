import { useState, FormEvent } from 'react';
import { TrainingGoal } from '../types';

interface TrainingGoalFormProps {
  onSubmit: (goal: TrainingGoal) => void;
  loading?: boolean;
}

const EVENT_OPTIONS = [
  '50m Free',
  '100m Free',
  '200m Free',
  '400m Free',
  '100m Back',
  '100m Breast',
  '100m Fly',
  '200m IM',
];

const TIMEFRAME_OPTIONS = [
  '2 weeks',
  '4 weeks',
  '6 weeks',
  '8 weeks',
  '3 months',
  '6 months',
];

/**
 * Form to collect training goal parameters from the swimmer.
 */
export function TrainingGoalForm({ onSubmit, loading }: TrainingGoalFormProps) {
  const [event, setEvent] = useState('100m Free');
  const [customEvent, setCustomEvent] = useState('');
  const [isCustom, setIsCustom] = useState(false);
  const [targetTime, setTargetTime] = useState('');
  const [volumeMeters, setVolumeMeters] = useState(2000);
  const [timeframe, setTimeframe] = useState('4 weeks');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit({
      event: isCustom ? customEvent : event,
      target_time: targetTime,
      volume_meters: volumeMeters,
      timeframe,
    });
  };

  return (
    <section className="training-goal-form" aria-label="Training goal">
      <h2 className="training-goal-form__heading">Set Your Training Goal</h2>
      <form onSubmit={handleSubmit} className="training-goal-form__form">
        <div className="training-goal-form__field">
          <label htmlFor="goal-event" className="training-goal-form__label">
            Target Event
          </label>
          <select
            id="goal-event"
            className="training-goal-form__select"
            value={isCustom ? '__custom__' : event}
            onChange={(e) => {
              if (e.target.value === '__custom__') {
                setIsCustom(true);
              } else {
                setIsCustom(false);
                setEvent(e.target.value);
              }
            }}
          >
            {EVENT_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
            <option value="__custom__">Custom...</option>
          </select>
          {isCustom && (
            <input
              type="text"
              className="training-goal-form__input"
              placeholder="e.g. 800m Free"
              value={customEvent}
              onChange={(e) => setCustomEvent(e.target.value)}
              required
            />
          )}
        </div>

        <div className="training-goal-form__field">
          <label htmlFor="goal-time" className="training-goal-form__label">
            Target Time
          </label>
          <input
            id="goal-time"
            type="text"
            className="training-goal-form__input"
            placeholder='e.g. 1:05 or 5:30'
            value={targetTime}
            onChange={(e) => setTargetTime(e.target.value)}
            required
          />
        </div>

        <div className="training-goal-form__field">
          <label htmlFor="goal-volume" className="training-goal-form__label">
            Session Volume (metres)
          </label>
          <input
            id="goal-volume"
            type="number"
            className="training-goal-form__input"
            min={500}
            max={10000}
            step={100}
            value={volumeMeters}
            onChange={(e) => setVolumeMeters(Number(e.target.value))}
            required
          />
        </div>

        <div className="training-goal-form__field">
          <label htmlFor="goal-timeframe" className="training-goal-form__label">
            Timeframe
          </label>
          <select
            id="goal-timeframe"
            className="training-goal-form__select"
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
          >
            {TIMEFRAME_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          className="training-goal-form__submit"
          disabled={loading}
        >
          {loading ? 'Generating...' : 'Generate Training Plan'}
        </button>
      </form>
    </section>
  );
}
