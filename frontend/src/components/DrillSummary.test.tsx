import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DrillSummary, computeDrillStats } from './DrillSummary';
import { LengthSplit } from '../types';

function makeSplit(overrides: Partial<LengthSplit> = {}): LengthSplit {
  return {
    length_number: 1,
    time_seconds: 30,
    stroke: 'freestyle',
    strokes: 12,
    ...overrides,
  };
}

describe('computeDrillStats', () => {
  it('returns null when no drill splits exist', () => {
    const splits = [makeSplit({ stroke: 'freestyle' }), makeSplit({ stroke: 'backstroke' })];
    expect(computeDrillStats(splits, 25)).toBeNull();
  });

  it('returns null for empty splits array', () => {
    expect(computeDrillStats([], 25)).toBeNull();
  });

  it('computes correct stats for drill splits', () => {
    const splits = [
      makeSplit({ stroke: 'drill', time_seconds: 45 }),
      makeSplit({ stroke: 'freestyle', time_seconds: 30 }),
      makeSplit({ stroke: 'drill', time_seconds: 55 }),
    ];
    const stats = computeDrillStats(splits, 25);
    expect(stats).toEqual({
      count: 2,
      totalDistance: 50,
      totalTime: 100,
    });
  });

  it('computes distance using pool length', () => {
    const splits = [
      makeSplit({ stroke: 'drill', time_seconds: 40 }),
      makeSplit({ stroke: 'drill', time_seconds: 50 }),
      makeSplit({ stroke: 'drill', time_seconds: 60 }),
    ];
    const stats = computeDrillStats(splits, 50);
    expect(stats).toEqual({
      count: 3,
      totalDistance: 150,
      totalTime: 150,
    });
  });
});

describe('DrillSummary', () => {
  it('returns null when no drill splits exist', () => {
    const splits = [makeSplit({ stroke: 'freestyle' })];
    const { container } = render(<DrillSummary splits={splits} poolLengthM={25} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders drill summary section with aria-label', () => {
    const splits = [makeSplit({ stroke: 'drill', time_seconds: 60 })];
    render(<DrillSummary splits={splits} poolLengthM={25} />);
    const section = screen.getByRole('region', { name: 'Drill summary' });
    expect(section).toBeInTheDocument();
  });

  it('displays drill count', () => {
    const splits = [
      makeSplit({ stroke: 'drill', time_seconds: 30 }),
      makeSplit({ stroke: 'drill', time_seconds: 40 }),
    ];
    render(<DrillSummary splits={splits} poolLengthM={25} />);
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('Lengths')).toBeInTheDocument();
  });

  it('displays total distance', () => {
    const splits = [
      makeSplit({ stroke: 'drill', time_seconds: 30 }),
      makeSplit({ stroke: 'drill', time_seconds: 40 }),
    ];
    render(<DrillSummary splits={splits} poolLengthM={50} />);
    expect(screen.getByText('100m')).toBeInTheDocument();
    expect(screen.getByText('Distance')).toBeInTheDocument();
  });

  it('displays formatted time', () => {
    const splits = [
      makeSplit({ stroke: 'drill', time_seconds: 90 }),
      makeSplit({ stroke: 'drill', time_seconds: 60 }),
    ];
    render(<DrillSummary splits={splits} poolLengthM={25} />);
    expect(screen.getByText('2:30')).toBeInTheDocument();
    expect(screen.getByText('Time')).toBeInTheDocument();
  });

  it('formats time with zero seconds correctly', () => {
    const splits = [makeSplit({ stroke: 'drill', time_seconds: 120 })];
    render(<DrillSummary splits={splits} poolLengthM={25} />);
    expect(screen.getByText('2:00')).toBeInTheDocument();
  });
});
