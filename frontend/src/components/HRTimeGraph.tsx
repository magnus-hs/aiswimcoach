import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import './HRTimeGraph.css';

interface HRTimePoint {
  t: number;
  hr: number;
}

type XAxisMode = 'time' | 'distance';

interface HRTimeGraphProps {
  hrTimeseries?: HRTimePoint[] | null;
  totalDistanceM?: number;
  totalTimeSeconds?: number;
}

/**
 * Heart rate over time/distance graph.
 * Toggle between time (minutes) and distance (meters) on x-axis.
 */
export function HRTimeGraph({ hrTimeseries, totalDistanceM, totalTimeSeconds }: HRTimeGraphProps) {
  const [xMode, setXMode] = useState<XAxisMode>('time');

  if (!hrTimeseries || hrTimeseries.length < 2) return null;

  const sessionDuration = totalTimeSeconds || hrTimeseries[hrTimeseries.length - 1].t || 1;
  const sessionDistance = totalDistanceM || 0;

  // Build data with both time and distance x values
  const data = hrTimeseries.map(p => {
    const timeMin = Math.round((p.t / 60) * 10) / 10;
    // Estimate distance linearly from time proportion
    const distanceM = sessionDistance > 0
      ? Math.round((p.t / sessionDuration) * sessionDistance)
      : 0;
    return { timeMin, distanceM, hr: p.hr };
  });

  const hrs = data.map(d => d.hr);
  const minHR = Math.min(...hrs);
  const maxHR = Math.max(...hrs);
  const avgHR = Math.round(hrs.reduce((a, b) => a + b, 0) / hrs.length);

  const canShowDistance = sessionDistance > 0;
  const xDataKey = xMode === 'time' ? 'timeMin' : 'distanceM';
  const xLabel = xMode === 'time' ? 'Time (min)' : 'Distance (m)';
  const tooltipLabel = xMode === 'time'
    ? (label: number) => `${label} min`
    : (label: number) => `${label}m`;

  return (
    <section className="hr-time-graph" aria-label="Heart rate over time">
      <div className="hr-time-graph__header">
        <h2 className="hr-time-graph__heading">Heart Rate Over Session</h2>
        {canShowDistance && (
          <div className="hr-time-graph__toggle">
            <button
              className={`hr-time-graph__toggle-btn ${xMode === 'time' ? 'hr-time-graph__toggle-btn--active' : ''}`}
              onClick={() => setXMode('time')}
            >
              Time
            </button>
            <button
              className={`hr-time-graph__toggle-btn ${xMode === 'distance' ? 'hr-time-graph__toggle-btn--active' : ''}`}
              onClick={() => setXMode('distance')}
            >
              Distance
            </button>
          </div>
        )}
      </div>
      <div className="hr-time-graph__summary">
        <span className="hr-time-graph__stat">
          Avg <strong>{avgHR}</strong> bpm
        </span>
        <span className="hr-time-graph__stat">
          Max <strong>{maxHR}</strong> bpm
        </span>
        <span className="hr-time-graph__stat">
          Min <strong>{minHR}</strong> bpm
        </span>
      </div>
      <div className="hr-time-graph__chart">
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-gray-200)" />
            <XAxis
              dataKey={xDataKey}
              tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
              label={{ value: xLabel, position: 'insideBottom', offset: -2, fontSize: 10, fill: 'var(--color-text-muted)' }}
            />
            <YAxis
              domain={[Math.max(0, minHR - 10), maxHR + 10]}
              tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
              label={{ value: 'HR (bpm)', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--color-text-muted)' }}
              width={45}
            />
            <Tooltip
              formatter={(value: number) => [`${value} bpm`, 'Heart Rate']}
              labelFormatter={tooltipLabel}
              contentStyle={{ fontSize: '12px', borderRadius: '6px' }}
            />
            <ReferenceLine
              y={avgHR}
              stroke="var(--color-text-muted)"
              strokeDasharray="4 4"
              strokeWidth={1}
            />
            <Line
              type="monotone"
              dataKey="hr"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
