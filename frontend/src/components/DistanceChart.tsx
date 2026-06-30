import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  Cell,
} from 'recharts';
import './DistanceChart.css';

export interface DistanceChartPoint {
  label: string;
  distance: number;
  startDate?: string;  // ISO date for filtering
  endDate?: string;    // ISO date for filtering
}

interface DistanceChartProps {
  data: DistanceChartPoint[];
  height?: number;
  onBarClick?: (point: DistanceChartPoint) => void;
}

/**
 * Compact bar chart showing distance over time periods.
 * Used in the sidebar to visualize weekly/monthly/yearly distance.
 */
export function DistanceChart({ data, height = 100, onBarClick }: DistanceChartProps) {
  if (data.length === 0) {
    return null;
  }

  const maxDistance = Math.max(...data.map(d => d.distance));
  const showAsKm = maxDistance >= 1000;

  // Format Y-axis tick values
  const formatYAxis = (value: number): string => {
    if (showAsKm) {
      const km = value / 1000;
      return km % 1 === 0 ? `${km.toFixed(0)}` : `${km.toFixed(1)}`;
    }
    return `${value}`;
  };

  const handleClick = (barData: any) => {
    if (onBarClick && barData?.activePayload?.[0]?.payload) {
      onBarClick(barData.activePayload[0].payload as DistanceChartPoint);
    }
  };

  return (
    <div className="distance-chart" aria-label="Distance chart">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          margin={{ top: 4, right: 4, left: -10, bottom: 0 }}
          onClick={onBarClick ? handleClick : undefined}
          style={onBarClick ? { cursor: 'pointer' } : undefined}
        >
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 9, fill: 'var(--color-text-muted)' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={formatYAxis}
            width={35}
            domain={[0, 'auto']}
          />
          <Tooltip
            formatter={(value: number) =>
              value >= 1000
                ? [`${(value / 1000).toFixed(1)} km`, 'Distance']
                : [`${value} m`, 'Distance']
            }
            contentStyle={{
              fontSize: '11px',
              padding: '4px 8px',
              borderRadius: '4px',
            }}
          />
          <Bar
            dataKey="distance"
            fill="var(--color-primary)"
            radius={[2, 2, 0, 0]}
          >
            {onBarClick && data.map((_, idx) => (
              <Cell key={idx} cursor="pointer" />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
