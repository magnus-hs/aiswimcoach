import './AppPreview.css';

/**
 * Mock "expanded interval set" preview — shows what a swimmer sees when they
 * expand a rep to view per-length detail (time, strokes, DPS, stroke, HR).
 */
function IntervalPreview() {
  const rows = [
    { n: 1, time: '21.8s', strokes: 9, dps: '2.78m', hr: 132 },
    { n: 2, time: '22.1s', strokes: 10, dps: '2.50m', hr: 138 },
    { n: 3, time: '22.4s', strokes: 10, dps: '2.50m', hr: 141 },
    { n: 4, time: '21.9s', strokes: 9, dps: '2.78m', hr: 137 },
  ];
  return (
    <div className="app-preview__card">
      <div className="app-preview__card-title">Session Structure</div>
      <div className="app-preview__interval-row app-preview__interval-row--summary">
        <span className="app-preview__arrow app-preview__arrow--open">▶</span>
        <span className="app-preview__dist">100m</span>
        <span className="app-preview__time">1:28.2</span>
        <span className="app-preview__stroke">Freestyle</span>
        <span className="app-preview__pace">1:28 /100m</span>
      </div>
      <div className="app-preview__detail">
        <table className="app-preview__table">
          <thead>
            <tr>
              <th>#</th><th>Time</th><th>Strokes</th><th>DPS</th><th>HR</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.n}>
                <td>{r.n}</td>
                <td>{r.time}</td>
                <td>{r.strokes}</td>
                <td>{r.dps}</td>
                <td className="app-preview__hr">{r.hr}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="app-preview__rest-badge">Rest 22s</div>
    </div>
  );
}

/**
 * Mock efficiency curve — stroke rate (x) vs pace (y) scatter with a
 * highlighted "sweet spot" point.
 */
function EfficiencyPreview() {
  const points = [
    [30, 62], [45, 50], [60, 40], [78, 30], [95, 26], [120, 22], [150, 34], [175, 46],
  ];
  return (
    <div className="app-preview__card">
      <div className="app-preview__card-title">Efficiency Curve</div>
      <div className="app-preview__card-subtitle">Stroke Rate vs Pace — find your sweet spot</div>
      <svg viewBox="0 0 200 90" className="app-preview__chart">
        <line x1="10" y1="80" x2="195" y2="80" stroke="var(--color-gray-300)" strokeWidth="1" />
        <line x1="10" y1="10" x2="10" y2="80" stroke="var(--color-gray-300)" strokeWidth="1" />
        {points.map(([x, y], i) => (
          <circle
            key={i}
            cx={10 + x}
            cy={y}
            r={i === 4 ? 5 : 3}
            fill={i === 4 ? 'hsl(45,95%,55%)' : 'var(--color-primary)'}
            opacity={i === 4 ? 1 : 0.75}
          />
        ))}
      </svg>
      <div className="app-preview__legend">
        <span className="app-preview__legend-dot app-preview__legend-dot--gold" /> Sweet spot: <strong>95 spm</strong> at <strong>1:26/100m</strong>
      </div>
    </div>
  );
}

/**
 * Mock heart rate over time line chart.
 */
function HeartRatePreview() {
  const points = [30, 40, 46, 52, 58, 62, 68, 60, 55, 50, 44, 38];
  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${10 + i * 15} ${80 - p}`)
    .join(' ');
  return (
    <div className="app-preview__card">
      <div className="app-preview__card-title">Heart Rate Over Time</div>
      <div className="app-preview__card-subtitle">Zone 5 · 90–100% max HR</div>
      <svg viewBox="0 0 200 90" className="app-preview__chart">
        <path d={path} fill="none" stroke="var(--color-error)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="app-preview__stats-row">
        <span>Avg <strong>158</strong> bpm</span>
        <span>Peak <strong>174</strong> bpm</span>
      </div>
    </div>
  );
}

/**
 * Mock SWOLF technique drift chart.
 */
function SwolfPreview() {
  const points = [36, 37, 38, 39, 40, 41, 43, 44];
  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${10 + i * 25} ${80 - (p - 30) * 4}`)
    .join(' ');
  return (
    <div className="app-preview__card">
      <div className="app-preview__card-title">SWOLF Technique</div>
      <div className="app-preview__card-subtitle">Drift under fatigue</div>
      <svg viewBox="0 0 200 90" className="app-preview__chart">
        <path d={path} fill="none" stroke="hsl(45,95%,55%)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="app-preview__stats-row">
        <span>Start <strong>36</strong></span>
        <span>End <strong>44</strong></span>
      </div>
    </div>
  );
}

/**
 * "See it in action" preview grid — illustrative mockups styled to match the
 * real app UI, giving visitors a sense of what they'll see after signing up.
 * Not live data — for illustration only.
 */
export function AppPreview() {
  return (
    <div className="app-preview">
      <IntervalPreview />
      <EfficiencyPreview />
      <HeartRatePreview />
      <SwolfPreview />
    </div>
  );
}
