import { useState, useEffect, FormEvent } from 'react';
import { getUserSessions } from '../api/sessionService';
import './GoalsPage.css';

interface Goals {
  focus?: string[];
  weekly_distance_m?: number;
  monthly_distance_m?: number;
  yearly_distance_m?: number;
  target_event?: string;
  target_time_seconds?: number;
  target_date?: string;
  notes?: string;
}

/** Qualitative focus goals the swimmer can pick. */
const FOCUS_OPTIONS: { key: string; label: string; icon: string }[] = [
  { key: 'endurance', label: 'Build endurance / swim further', icon: '🫁' },
  { key: 'speed', label: 'Get faster (sprint speed)', icon: '⚡' },
  { key: 'technique', label: 'Improve technique & efficiency', icon: '🌊' },
  { key: 'css', label: 'Improve CSS / threshold', icon: '📈' },
  { key: 'race', label: 'Prepare for a race / event', icon: '🏁' },
  { key: 'consistency', label: 'Swim more consistently', icon: '📅' },
  { key: 'weight', label: 'Fitness & weight management', icon: '❤️' },
  { key: 'open_water', label: 'Open water swimming', icon: '🌅' },
];

const STROKES = ['Freestyle', 'Backstroke', 'Breaststroke', 'Butterfly', 'IM'];
const DISTANCES = ['50m', '100m', '200m', '400m', '800m', '1500m'];

function parseTime(input: string): number | null {
  const t = input.trim();
  if (!t) return null;
  const m = t.match(/^(\d{1,3}):(\d{2})(?:\.(\d{1,2}))?$/);
  if (m) {
    const secs = parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
    return m[3] ? secs + parseFloat(`0.${m[3]}`) : secs;
  }
  const n = Number(t);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/** Start of the current week (Monday, local time). */
function weekStart(): Date {
  const now = new Date();
  const day = (now.getDay() + 6) % 7; // Mon=0
  const d = new Date(now);
  d.setDate(now.getDate() - day);
  d.setHours(0, 0, 0, 0);
  return d;
}

/** Start of the current month (local time). */
function monthStart(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0);
}

/** Start of the current year (local time). */
function yearStart(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), 0, 1, 0, 0, 0, 0);
}

type Period = 'week' | 'month' | 'year';

/**
 * Goals page — set qualitative and measurable swimming goals that steer the AI
 * coach's analysis and comparisons.
 */
export function GoalsPage() {
  const [focus, setFocus] = useState<string[]>([]);
  const [weeklyKm, setWeeklyKm] = useState('');
  const [monthlyKm, setMonthlyKm] = useState('');
  const [yearlyKm, setYearlyKm] = useState('');
  const [activePeriod, setActivePeriod] = useState<Period>('week');
  const [stroke, setStroke] = useState('Freestyle');
  const [distance, setDistance] = useState('100m');
  const [targetTime, setTargetTime] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [notes, setNotes] = useState('');

  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [weekDistance, setWeekDistance] = useState<number | null>(null);
  const [monthDistance, setMonthDistance] = useState<number | null>(null);
  const [yearDistance, setYearDistance] = useState<number | null>(null);

  useEffect(() => {
    loadGoals();
    loadDistances();
  }, []);

  const loadGoals = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) return;
      const res = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/profile/goals`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      const g: Goals = data.goals || {};
      if (g.focus) setFocus(g.focus);
      if (g.weekly_distance_m) setWeeklyKm((g.weekly_distance_m / 1000).toString());
      if (g.monthly_distance_m) setMonthlyKm((g.monthly_distance_m / 1000).toString());
      if (g.yearly_distance_m) setYearlyKm((g.yearly_distance_m / 1000).toString());
      if (g.target_event) {
        const parts = g.target_event.split(' ');
        if (parts[0]) setDistance(parts[0]);
        if (parts[1]) setStroke(parts[1]);
      }
      if (g.target_time_seconds) setTargetTime(formatTime(g.target_time_seconds));
      if (g.target_date) setTargetDate(g.target_date);
      if (g.notes) setNotes(g.notes);
    } catch {
      // non-critical
    }
  };

  const loadDistances = async () => {
    try {
      const sessions = await getUserSessions();
      const ws = weekStart();
      const ms = monthStart();
      const ys = yearStart();
      let week = 0;
      let month = 0;
      let year = 0;
      for (const s of sessions) {
        const d = new Date(s.session_date);
        if (d >= ws) week += s.total_distance_meters;
        if (d >= ms) month += s.total_distance_meters;
        if (d >= ys) year += s.total_distance_meters;
      }
      setWeekDistance(week);
      setMonthDistance(month);
      setYearDistance(year);
    } catch {
      // non-critical
    }
  };

  const toggleFocus = (key: string) => {
    setFocus((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    const goals: Goals = {};
    if (focus.length > 0) goals.focus = focus;

    const parseKm = (val: string, label: string): number | null | 'error' => {
      if (!val.trim()) return null;
      const km = Number(val);
      if (!Number.isFinite(km) || km <= 0) {
        setError(`${label} goal must be a positive number of km.`);
        return 'error';
      }
      return Math.round(km * 1000);
    };

    const wk = parseKm(weeklyKm, 'Weekly');
    if (wk === 'error') return;
    if (wk) goals.weekly_distance_m = wk;

    const mo = parseKm(monthlyKm, 'Monthly');
    if (mo === 'error') return;
    if (mo) goals.monthly_distance_m = mo;

    const yr = parseKm(yearlyKm, 'Yearly');
    if (yr === 'error') return;
    if (yr) goals.yearly_distance_m = yr;

    if (targetTime.trim()) {
      const secs = parseTime(targetTime);
      if (secs === null) {
        setError('Target time must be in M:SS format (e.g., 1:25).');
        return;
      }
      goals.target_time_seconds = secs;
      goals.target_event = `${distance} ${stroke}`;
    }

    if (targetDate) goals.target_date = targetDate;
    if (notes.trim()) goals.notes = notes.trim();

    setSaving(true);
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/profile/goals`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ goals }),
      });
      if (!res.ok) throw new Error('save failed');
      setSuccess(true);
    } catch {
      setError('Failed to save goals. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const periodConfig: Record<Period, { label: string; km: string; setKm: (v: string) => void; distance: number | null; suffix: string }> = {
    week: { label: 'Per Week', km: weeklyKm, setKm: setWeeklyKm, distance: weekDistance, suffix: 'this week' },
    month: { label: 'Per Month', km: monthlyKm, setKm: setMonthlyKm, distance: monthDistance, suffix: 'this month' },
    year: { label: 'Per Year', km: yearlyKm, setKm: setYearlyKm, distance: yearDistance, suffix: 'this year' },
  };
  const active = periodConfig[activePeriod];
  const activeGoalM = active.km.trim() ? Math.round(Number(active.km) * 1000) : null;
  const activePct =
    activeGoalM && active.distance != null && activeGoalM > 0
      ? Math.min(100, Math.round((active.distance / activeGoalM) * 100))
      : null;

  return (
    <div className="goals-page">
      <h1 className="goals-page__heading">My Goals</h1>
      <p className="goals-page__intro">
        Set what you want to achieve. Your goals steer the AI coach's analysis — it will compare
        your sessions against them and tell you how close you are and what to do next.
      </p>

      <form className="goals-page__form" onSubmit={handleSave}>
        <section className="goals-page__card">
          <h2>What do you want to work on?</h2>
          <p className="goals-page__hint">Pick any that apply.</p>
          <div className="goals-page__chips">
            {FOCUS_OPTIONS.map((opt) => {
              const active = focus.includes(opt.key);
              return (
                <button
                  type="button"
                  key={opt.key}
                  className={`goals-page__chip ${active ? 'goals-page__chip--active' : ''}`}
                  onClick={() => toggleFocus(opt.key)}
                  aria-pressed={active}
                >
                  <span className="goals-page__chip-icon">{opt.icon}</span>
                  {opt.label}
                </button>
              );
            })}
          </div>
        </section>

        <section className="goals-page__card">
          <h2>Distance goals</h2>
          <p className="goals-page__hint">Measurable targets for how far you want to swim. Set any or all.</p>
          <div className="goals-page__tabs" role="tablist">
            {(['week', 'month', 'year'] as Period[]).map((p) => (
              <button
                type="button"
                key={p}
                role="tab"
                aria-selected={activePeriod === p}
                className={`goals-page__tab ${activePeriod === p ? 'goals-page__tab--active' : ''}`}
                onClick={() => setActivePeriod(p)}
              >
                {periodConfig[p].label}
                {periodConfig[p].km.trim() && <span className="goals-page__tab-dot" aria-hidden="true">•</span>}
              </button>
            ))}
          </div>
          <div className="goals-page__field">
            <label htmlFor="period-km">Distance {active.label.toLowerCase()} (km)</label>
            <input
              id="period-km"
              type="number"
              min="0"
              step="0.5"
              value={active.km}
              onChange={(e) => active.setKm(e.target.value)}
              placeholder="e.g. 10"
              className="goals-page__input"
            />
          </div>
          {activeGoalM && active.distance != null && (
            <div className="goals-page__progress">
              <div className="goals-page__progress-label">
                {active.suffix.charAt(0).toUpperCase() + active.suffix.slice(1)}: {active.distance}m of {activeGoalM}m ({activePct}%)
              </div>
              <div className="goals-page__progress-bar">
                <div
                  className="goals-page__progress-fill"
                  style={{ width: `${activePct ?? 0}%` }}
                />
              </div>
            </div>
          )}
        </section>

        <section className="goals-page__card">
          <h2>Target race time</h2>
          <p className="goals-page__hint">Optional — a specific event and time you're aiming for.</p>
          <div className="goals-page__row">
            <div className="goals-page__field">
              <label htmlFor="goal-distance">Distance</label>
              <select
                id="goal-distance"
                className="goals-page__input"
                value={distance}
                onChange={(e) => setDistance(e.target.value)}
              >
                {DISTANCES.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
            <div className="goals-page__field">
              <label htmlFor="goal-stroke">Stroke</label>
              <select
                id="goal-stroke"
                className="goals-page__input"
                value={stroke}
                onChange={(e) => setStroke(e.target.value)}
              >
                {STROKES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div className="goals-page__field">
              <label htmlFor="goal-time">Target time (M:SS)</label>
              <input
                id="goal-time"
                type="text"
                value={targetTime}
                onChange={(e) => setTargetTime(e.target.value)}
                placeholder="e.g. 1:25"
                className="goals-page__input"
              />
            </div>
          </div>
          <div className="goals-page__field">
            <label htmlFor="goal-date">Target date (optional)</label>
            <input
              id="goal-date"
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="goals-page__input"
            />
          </div>
        </section>

        <section className="goals-page__card">
          <h2>Anything else?</h2>
          <div className="goals-page__field">
            <label htmlFor="goal-notes">Notes for your coach (optional)</label>
            <textarea
              id="goal-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Coming back from a shoulder injury, want to rebuild gradually."
              className="goals-page__input goals-page__textarea"
              rows={3}
              maxLength={500}
            />
          </div>
        </section>

        {error && <p className="goals-page__error" role="alert">{error}</p>}
        {success && <p className="goals-page__success">Goals saved! Your AI coach will use these.</p>}

        <button type="submit" className="goals-page__submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save Goals'}
        </button>
      </form>
    </div>
  );
}
