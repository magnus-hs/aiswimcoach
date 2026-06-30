import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { LengthSplit } from '../types';
import './EfficiencyCurve.css';

interface EfficiencyCurveProps {
  splits: LengthSplit[];
  poolLengthM: number;
}

interface EfficiencyPoint {
  strokeRate: number;  // strokes per minute
  pace: number;        // seconds per 100m
  lengthNumber: number;
}

/**
 * Efficiency Curve: Stroke Rate (x) vs Pace (y) scatter plot.
 * Shows the "sweet spot" where efficiency is maximized (low pace at moderate stroke rate).
 */
export function EfficiencyCurve({ splits, poolLengthM }: EfficiencyCurveProps) {
  // Only render with meaningful data
  const validSplits = splits.filter(s => s.strokes > 0 && s.time_seconds > 0);
  if (validSplits.length < 3) return null;

  const data: EfficiencyPoint[] = validSplits.map(s => {
    const strokeRate = (s.strokes / s.time_seconds) * 60; // strokes/min
    const pace = (s.time_seconds / poolLengthM) * 100;     // sec/100m
    return {
      strokeRate: Math.round(strokeRate * 10) / 10,
      pace: Math.round(pace * 10) / 10,
      lengthNumber: s.length_number,
    };
  });

  const rates = data.map(d => d.strokeRate);
  const paces = data.map(d => d.pace);
  const minRate = Math.min(...rates);
  const maxRate = Math.max(...rates);
  const minPace = Math.min(...paces);
  const maxPace = Math.max(...paces);

  // Find the "sweet spot" — the point with lowest pace (fastest)
  const bestPoint = data.reduce((best, p) => p.pace < best.pace ? p : best, data[0]);

  return (
    <section className="efficiency-curve" aria-label="Efficiency curve analysis">
      <h2 className="efficiency-curve__heading">Efficiency Curve</h2>
      <p className="efficiency-curve__subtitle">
        Stroke Rate vs Pace — find your sweet spot
      </p>
      <div className="efficiency-curve__summary">
        <span className="efficiency-curve__stat">
          Sweet spot: <strong>{bestPoint.strokeRate} spm</strong> at <strong>{bestPoint.pace}s/100m</strong>
        </span>
      </div>
      <div className="efficiency-curve__chart">
        <ResponsiveContainer width="100%" height={220}>
          <ScatterChart margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-gray-200)" />
            <XAxis
              dataKey="strokeRate"
              type="number"
              domain={[Math.floor(minRate - 2), Math.ceil(maxRate + 2)]}
              tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
              label={{ value: 'Stroke Rate (spm)', position: 'insideBottom', offset: -5, fontSize: 10, fill: 'var(--color-text-muted)' }}
              name="Stroke Rate"
            />
            <YAxis
              dataKey="pace"
              type="number"
              domain={[Math.floor(minPace - 5), Math.ceil(maxPace + 5)]}
              tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
              label={{ value: 'Pace (s/100m)', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--color-text-muted)' }}
              width={45}
              name="Pace"
            />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === 'Stroke Rate') return [`${value} spm`, 'Stroke Rate'];
                return [`${value} s/100m`, 'Pace'];
              }}
              contentStyle={{ fontSize: '12px', borderRadius: '6px' }}
            />
            <Scatter
              data={data}
              fill="var(--color-primary)"
              fillOpacity={0.7}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
