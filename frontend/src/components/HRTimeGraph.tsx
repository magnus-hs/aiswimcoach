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

interface HRTimeGraphProps {
  hrTimeseries?: HRTimePoint[] | null;
}

/**
 * Heart rate over time graph using per-second HR data from the FIT file.
 * X-axis: session time (minutes)
 * Y-axis: heart rate (bpm)
 */
export function HRTimeGraph({ hrTimeseries }: HRTimeGraphProps) {
  if (!hrTimeseries || hrTimeseries.length < 2) return null;

  // Convert seconds to minutes for display
  const data = hrTimeseries.map(p => ({
    timeMin: Math.round((p.t / 60) * 10) / 10,
    hr: p.hr,
  }));

  const hrs = data.map(d => d.hr);
  const minHR = Math.min(...hrs);
  const maxHR = Math.max(...hrs);
  const avgHR = Math.round(hrs.reduce((a, b) => a + b, 0) / hrs.length);

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
              dataKey="timeMin"
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
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
