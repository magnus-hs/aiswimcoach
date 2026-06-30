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
import './StrokeMetricsCharts.css';

interface StrokeMetricsChartsProps {
  splits: LengthSplit[];
  poolLengthM: number;
}

interface MetricPoint {
  distance: number;
  dps: number;       // distance per stroke (meters)
  spm: number;       // strokes per minute
}

/**
 * Two charts: Distance Per Stroke and Strokes Per Minute over session distance.
 */
export function StrokeMetricsCharts({ splits, poolLengthM }: StrokeMetricsChartsProps) {
  const validSplits = splits.filter(s => s.strokes > 0 && s.time_seconds > 0);
  if (validSplits.length < 2) return null;

  let cumDistance = 0;
  const data: MetricPoint[] = validSplits.map(s => {
    cumDistance += poolLengthM;
    const dps = poolLengthM / s.strokes;
    const spm = (s.strokes / s.time_seconds) * 60;
    return {
      distance: cumDistance,
      dps: Math.round(dps * 100) / 100,
      spm: Math.round(spm * 10) / 10,
    };
  });

  const avgDps = data.reduce((sum, d) => sum + d.dps, 0) / data.length;
  const avgSpm = data.reduce((sum, d) => sum + d.spm, 0) / data.length;

  return (
    <div className="stroke-metrics">
      <section className="stroke-metrics__chart-section" aria-label="Distance per stroke">
        <h2 className="stroke-metrics__heading">Distance Per Stroke</h2>
        <p className="stroke-metrics__avg">Avg: <strong>{avgDps.toFixed(2)}m</strong> per stroke</p>
        <div className="stroke-metrics__chart">
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-gray-300)" />
              <XAxis
                dataKey="distance"
                tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                label={{ value: 'Distance (m)', position: 'insideBottom', offset: -2, fontSize: 10, fill: 'var(--color-text-muted)' }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                width={40}
                domain={['auto', 'auto']}
                label={{ value: 'm/stroke', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--color-text-muted)' }}
              />
              <Tooltip
                formatter={(value: number) => [`${value}m`, 'Dist/Stroke']}
                labelFormatter={(label: number) => `${label}m`}
                contentStyle={{ fontSize: '12px', borderRadius: '6px', background: 'var(--color-surface)', border: '1px solid var(--color-gray-300)' }}
              />
              <ReferenceLine y={avgDps} stroke="var(--color-text-muted)" strokeDasharray="4 4" />
              <Line type="monotone" dataKey="dps" stroke="var(--color-secondary)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="stroke-metrics__chart-section" aria-label="Strokes per minute">
        <h2 className="stroke-metrics__heading">Strokes Per Minute</h2>
        <p className="stroke-metrics__avg">Avg: <strong>{avgSpm.toFixed(1)} spm</strong></p>
        <div className="stroke-metrics__chart">
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-gray-300)" />
              <XAxis
                dataKey="distance"
                tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                label={{ value: 'Distance (m)', position: 'insideBottom', offset: -2, fontSize: 10, fill: 'var(--color-text-muted)' }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                width={40}
                domain={['auto', 'auto']}
                label={{ value: 'spm', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--color-text-muted)' }}
              />
              <Tooltip
                formatter={(value: number) => [`${value} spm`, 'Stroke Rate']}
                labelFormatter={(label: number) => `${label}m`}
                contentStyle={{ fontSize: '12px', borderRadius: '6px', background: 'var(--color-surface)', border: '1px solid var(--color-gray-300)' }}
              />
              <ReferenceLine y={avgSpm} stroke="var(--color-text-muted)" strokeDasharray="4 4" />
              <Line type="monotone" dataKey="spm" stroke="var(--color-primary)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
