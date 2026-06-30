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
import './SwolfChart.css';

interface SwolfChartProps {
  splits: LengthSplit[];
  poolLengthM: number;
}

interface SwolfPoint {
  distance: number;
  swolf: number;
  lengthNumber: number;
}

/**
 * SWOLF technique chart: shows how technique degrades over a session.
 * SWOLF = time_seconds + strokes for each length.
 * X-axis: cumulative distance (m)
 * Y-axis: SWOLF score
 * Color gradient from green (good) to red (fatigued).
 */
export function SwolfChart({ splits, poolLengthM }: SwolfChartProps) {
  // Only render if we have meaningful data
  const validSplits = splits.filter(s => s.time_seconds > 0);
  if (validSplits.length < 2) return null;

  // For SWOLF, only include lengths with strokes > 0
  const swolfSplits = validSplits.filter(s => s.strokes > 0);
  if (swolfSplits.length < 2) return null;

  let cumDistance = 0;
  const data: SwolfPoint[] = swolfSplits.map(s => {
    cumDistance += poolLengthM;
    return {
      distance: cumDistance,
      swolf: Math.round(s.time_seconds + s.strokes),
      lengthNumber: s.length_number,
    };
  });

  const swolfs = data.map(d => d.swolf);
  const minSwolf = Math.min(...swolfs);
  const maxSwolf = Math.max(...swolfs);
  const avgSwolf = Math.round(swolfs.reduce((a, b) => a + b, 0) / swolfs.length);
  const drift = data[data.length - 1].swolf - data[0].swolf;

  return (
    <section className="swolf-chart" aria-label="SWOLF technique analysis">
      <h2 className="swolf-chart__heading">Technique (SWOLF) Over Session</h2>
      <div className="swolf-chart__summary">
        <span className="swolf-chart__stat">
          Avg <strong>{avgSwolf}</strong>
        </span>
        <span className="swolf-chart__stat">
          Best <strong>{minSwolf}</strong>
        </span>
        <span className="swolf-chart__stat">
          Worst <strong>{maxSwolf}</strong>
        </span>
        <span className={`swolf-chart__stat ${drift > 2 ? 'swolf-chart__stat--warn' : ''}`}>
          Drift <strong>{drift > 0 ? '+' : ''}{drift}</strong>
        </span>
      </div>
      <div className="swolf-chart__chart">
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-gray-200)" />
            <XAxis
              dataKey="distance"
              tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
              label={{ value: 'Distance (m)', position: 'insideBottom', offset: -2, fontSize: 10, fill: 'var(--color-text-muted)' }}
            />
            <YAxis
              domain={[Math.max(0, minSwolf - 3), maxSwolf + 3]}
              tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
              label={{ value: 'SWOLF', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--color-text-muted)' }}
              width={40}
            />
            <Tooltip
              formatter={(value: number) => [`${value}`, 'SWOLF']}
              labelFormatter={(label: number) => `${label}m`}
              contentStyle={{ fontSize: '12px', borderRadius: '6px' }}
            />
            <ReferenceLine
              y={avgSwolf}
              stroke="var(--color-text-muted)"
              strokeDasharray="4 4"
              strokeWidth={1}
            />
            <Line
              type="monotone"
              dataKey="swolf"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={{ fill: '#f59e0b', r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {drift > 2 && (
        <p className="swolf-chart__insight">
          ⚠️ Your SWOLF drifted by +{drift} from start to finish — technique breakdown under fatigue detected.
        </p>
      )}
    </section>
  );
}
