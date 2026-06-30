import { useState, useEffect, FormEvent } from 'react';
import './CSSPage.css';

/**
 * Critical Swim Speed (CSS) page.
 * Explains CSS, lets users enter 400m/200m times, calculates and saves CSS pace.
 */
export function CSSPage() {
  const [time400, setTime400] = useState('');
  const [time200, setTime200] = useState('');
  const [cssPace, setCssPace] = useState<number | null>(null);
  const [savedCss, setSavedCss] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadCss();
  }, []);

  const loadCss = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) return;
      const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/profile/css`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        if (data.css_pace_per_100m) {
          setSavedCss(data.css_pace_per_100m);
        }
      }
    } catch {
      // Non-critical
    }
  };

  const parseTime = (input: string): number | null => {
    const match = input.trim().match(/^(\d{1,2}):(\d{2})$/);
    if (!match) return null;
    return parseInt(match[1], 10) * 60 + parseInt(match[2], 10);
  };

  const calculate = () => {
    const t400 = parseTime(time400);
    const t200 = parseTime(time200);
    if (t400 === null || t200 === null) {
      setError('Enter times in M:SS format (e.g., 6:30)');
      setCssPace(null);
      return;
    }
    if (t400 <= t200) {
      setError('400m time must be greater than 200m time');
      setCssPace(null);
      return;
    }
    setError(null);
    // CSS pace per 100m = (T400 - T200) / 2
    const cssPer100 = (t400 - t200) / 2;
    setCssPace(Math.round(cssPer100 * 10) / 10);
  };

  useEffect(() => {
    if (time400 && time200) {
      calculate();
    }
  }, [time400, time200]);

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (cssPace === null) return;
    setSaving(true);
    setSuccess(false);
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/profile/css`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ css_pace_per_100m: cssPace }),
      });
      if (!response.ok) throw new Error('Failed to save');
      setSavedCss(cssPace);
      setSuccess(true);
    } catch (err) {
      setError('Failed to save CSS. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const formatPace = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="css-page">
      <h1 className="css-page__heading">Critical Swim Speed (CSS)</h1>

      <div className="css-page__explanation">
        <h2>What is CSS?</h2>
        <p>
          Critical Swim Speed is your <strong>threshold pace</strong> — the fastest pace you can sustain
          for an extended duration without accumulating excessive fatigue. It represents the boundary
          between aerobic and anaerobic swimming.
        </p>
        <p>
          CSS is used to categorize your training sets by energy system:
        </p>
        <ul>
          <li><strong>Sprint (Anaerobic):</strong> Faster than CSS by 5+ sec/100m</li>
          <li><strong>Threshold:</strong> Within ±5 sec/100m of CSS</li>
          <li><strong>Aerobic Endurance:</strong> Slower than CSS by 5+ sec/100m</li>
        </ul>
        <h3>How to calculate</h3>
        <p>
          Swim a <strong>400m time trial</strong> and a <strong>200m time trial</strong> (all-out effort for both).
          Your CSS pace per 100m is calculated as:
        </p>
        <p className="css-page__formula">
          CSS = (T<sub>400</sub> − T<sub>200</sub>) ÷ 2
        </p>
      </div>

      {savedCss && (
        <div className="css-page__current">
          <span className="css-page__current-label">Your current CSS:</span>
          <span className="css-page__current-value">{formatPace(savedCss)} /100m</span>
          <span className="css-page__current-seconds">({savedCss} sec/100m)</span>
        </div>
      )}

      <div className="css-page__form-card">
        <h2>Calculate Your CSS</h2>
        <form className="css-page__form" onSubmit={handleSave}>
          <div className="css-page__field">
            <label htmlFor="time-400">400m Time Trial</label>
            <input
              id="time-400"
              type="text"
              value={time400}
              onChange={(e) => setTime400(e.target.value)}
              placeholder="M:SS (e.g., 6:30)"
              className="css-page__input"
            />
          </div>
          <div className="css-page__field">
            <label htmlFor="time-200">200m Time Trial</label>
            <input
              id="time-200"
              type="text"
              value={time200}
              onChange={(e) => setTime200(e.target.value)}
              placeholder="M:SS (e.g., 3:00)"
              className="css-page__input"
            />
          </div>

          {error && <p className="css-page__error" role="alert">{error}</p>}

          {cssPace !== null && (
            <div className="css-page__result">
              <span className="css-page__result-label">Your CSS pace:</span>
              <span className="css-page__result-value">{formatPace(cssPace)} /100m</span>
            </div>
          )}

          {success && <p className="css-page__success">CSS saved successfully!</p>}

          <button
            type="submit"
            className="css-page__submit"
            disabled={saving || cssPace === null}
          >
            {saving ? 'Saving…' : 'Save CSS'}
          </button>
        </form>
      </div>
    </div>
  );
}
