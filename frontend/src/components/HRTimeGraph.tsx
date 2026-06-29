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
import { LengthSplit } from '../types';
import './HRTimeGraph.css';

interface HRTimeGraphProps {
  splits: LengthSplit[];
}

interface HRDataPoint {
  timeMinutes: number;
  hr: number;
  label: string;
}

/**
 * Heart rate over time graph built from per-length avg_hr data.
 * X-axis: cumulative session time (minutes)
 * Y-axis: heart rate (bpm)
 */
export function HRTimeGraph({ splits }: HRTimeGraphProps) {
  // Only render if we have HR data
  const splitsWithHR = splits.filter(s => s.avg_hr != null);
  if (splitsWithHR.length < 2) return null;

  // Build data points: cumulative time → HR
  let cumulativeSeconds = 0;
  const data: HRDataPoint[] = [];

  for (const split of splits) {
    cumulativeSeconds += split.time_seconds;
    if (split.avg_hr != null) {
      data.push({
        timeMinutes: Math.round((cumulativeSeconds / 60) * 10) / 10,
        hr: split.avg_hr,
        label: `Length ${split.length_number}`,
      });
    }
    // Add rest time to cumulative
    if (split.rest_after_seconds) {
      cumulativeSeconds += split.rest_after_seconds;
    }
  }

  const minHR = Math.min(...data.map(d => d.hr));
  const maxHR = Math.max(...data.map(d => d.hr));
  const avgHR = Math.round(data.reduce((sum, d) => sum + d.hr, 0) / data.length);

  return (
    <section className="hr-time-graph" aria-label="Heart rate over time">
      <h2 className="hr-time-graph__heading">Heart Rate Over Session</h2>
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
              dataKey="timeMinutes"
              tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
              label={{ value: 'Time (min)', position: 'insideBottom', offset: -2, fontSize: 10, fill: 'var(--color-text-muted)' }}
            />
            <YAxis
              domain={[Math.max(0, minHR - 10), maxHR + 10]}
              tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
              label={{ value: 'HR (bpm)', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--color-text-muted)' }}
              width={45}
            />
            <Tooltip
              formatter={(value: number) => [`${value} bpm`, 'Heart Rate']}
              labelFormatter={(label: number) => `${label} min`}
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
              dot={{ fill: '#ef4444', r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
