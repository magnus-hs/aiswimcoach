import { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import './ProgressGraph.css';
import { SessionSummary } from '../api/sessionService';

export interface ProgressGraphProps {
  /** Array of session summaries */
  sessions: SessionSummary[];
}

type TimeRange = '7' | '30' | '90' | 'all';

interface ChartDataPoint {
  date: string;
  distance: number;
  displayDate: string;
}

/**
 * Aggregate sessions by date and sum total distances.
 */
function aggregateDailyDistances(sessions: SessionSummary[]): Map<string, number> {
  const dailyTotals = new Map<string, number>();

  for (const session of sessions) {
    // Extract date part from ISO 8601 timestamp (YYYY-MM-DD)
    const datePart = session.session_date.split('T')[0];
    const currentTotal = dailyTotals.get(datePart) || 0;
    dailyTotals.set(datePart, currentTotal + session.total_distance_meters);
  }

  return dailyTotals;
}

/**
 * Filter sessions based on selected time range.
 */
function filterSessionsByTimeRange(
  sessions: SessionSummary[],
  timeRange: TimeRange,
): SessionSummary[] {
  if (timeRange === 'all') {
    return sessions;
  }

  const days = parseInt(timeRange, 10);
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - days);

  return sessions.filter((session) => {
    const sessionDate = new Date(session.session_date);
    return sessionDate >= cutoffDate;
  });
}

/**
 * Format date for display on X-axis (e.g., "Jan 15").
 */
function formatDateForDisplay(dateStr: string): string {
  const date = new Date(dateStr);
  const month = date.toLocaleString('en-US', { month: 'short' });
  const day = date.getDate();
  return `${month} ${day}`;
}

/**
 * Prepare chart data from sessions for the selected time range.
 */
function prepareChartData(
  sessions: SessionSummary[],
  timeRange: TimeRange,
): ChartDataPoint[] {
  const filteredSessions = filterSessionsByTimeRange(sessions, timeRange);
  const dailyDistances = aggregateDailyDistances(filteredSessions);

  // Convert to array and sort by date
  const data: ChartDataPoint[] = Array.from(dailyDistances.entries())
    .map(([date, distance]) => ({
      date,
      distance,
      displayDate: formatDateForDisplay(date),
    }))
    .sort((a, b) => a.date.localeCompare(b.date));

  return data;
}

/**
 * Custom tooltip component for hover display.
 */
function CustomTooltip({ active, payload }: any) {
  if (active && payload && payload.length) {
    const data = payload[0].payload as ChartDataPoint;
    return (
      <div className="progress-graph__tooltip">
        <p className="progress-graph__tooltip-date">{data.displayDate}</p>
        <p className="progress-graph__tooltip-distance">{data.distance} meters</p>
      </div>
    );
  }
  return null;
}

/**
 * Line chart component showing total distance swum per day over time.
 *
 * Features:
 * - X-axis: dates in readable format (e.g., "Jan 15")
 * - Y-axis: distance in meters
 * - Time range selector: Last 7/30/90 Days, All Time
 * - Hover tooltip showing date and distance
 * - Blue color scheme (blue-500)
 *
 * Validates: Requirements 18.1-18.10
 */
export function ProgressGraph({ sessions }: ProgressGraphProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('30');

  const chartData = useMemo(
    () => prepareChartData(sessions, timeRange),
    [sessions, timeRange],
  );

  return (
    <section className="progress-graph" aria-label="Training progress graph">
      <div className="progress-graph__header">
        <h2 className="progress-graph__heading">Training Progress</h2>
        <div className="progress-graph__controls">
          <label htmlFor="time-range-select" className="progress-graph__label">
            Time Range:
          </label>
          <select
            id="time-range-select"
            className="progress-graph__select"
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as TimeRange)}
          >
            <option value="7">Last 7 Days</option>
            <option value="30">Last 30 Days</option>
            <option value="90">Last 90 Days</option>
            <option value="all">All Time</option>
          </select>
        </div>
      </div>

      {chartData.length === 0 ? (
        <div className="progress-graph__empty">
          <p>No session data available for the selected time range.</p>
        </div>
      ) : (
        <div className="progress-graph__chart-container">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="displayDate"
                stroke="#6b7280"
                style={{ fontSize: '12px' }}
              />
              <YAxis
                stroke="#6b7280"
                style={{ fontSize: '12px' }}
                label={{ value: 'Distance (m)', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="distance"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ fill: '#3b82f6', r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
