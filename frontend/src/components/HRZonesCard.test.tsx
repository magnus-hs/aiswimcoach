import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HRZonesCard } from './HRZonesCard';
import { HRZonesData } from '../types';

describe('HRZonesCard', () => {
  const mockHRZones: HRZonesData = {
    zone_1_seconds: 600,
    zone_2_seconds: 900,
    zone_3_seconds: 300,
    zone_4_seconds: 150,
    zone_5_seconds: 50,
    zone_1_percent: 30.0,
    zone_2_percent: 45.0,
    zone_3_percent: 15.0,
    zone_4_percent: 7.5,
    zone_5_percent: 2.5,
    max_hr: 180,
    zone_boundaries: {
      1: [90, 108],
      2: [108, 126],
      3: [126, 144],
      4: [144, 162],
      5: [162, 180],
    },
  };

  it('renders empty state when hrZones is null', () => {
    render(<HRZonesCard hrZones={null} />);
    
    expect(screen.getByText('Heart Rate Zones')).toBeInTheDocument();
    expect(
      screen.getByText('Heart rate data was not found in your FIT file')
    ).toBeInTheDocument();
  });

  it('renders empty state when hrZones is undefined', () => {
    render(<HRZonesCard hrZones={undefined} />);
    
    expect(
      screen.getByText('Heart rate data was not found in your FIT file')
    ).toBeInTheDocument();
  });

  it('renders zone list with all 5 zones', () => {
    render(<HRZonesCard hrZones={mockHRZones} />);
    
    expect(screen.getByText('Zone 1')).toBeInTheDocument();
    expect(screen.getByText('Zone 2')).toBeInTheDocument();
    expect(screen.getByText('Zone 3')).toBeInTheDocument();
    expect(screen.getByText('Zone 4')).toBeInTheDocument();
    expect(screen.getByText('Zone 5')).toBeInTheDocument();
  });

  it('displays HR range for each zone', () => {
    render(<HRZonesCard hrZones={mockHRZones} />);
    
    expect(screen.getByText('90-108 bpm')).toBeInTheDocument();
    expect(screen.getByText('108-126 bpm')).toBeInTheDocument();
    expect(screen.getByText('126-144 bpm')).toBeInTheDocument();
    expect(screen.getByText('144-162 bpm')).toBeInTheDocument();
    expect(screen.getByText('162-180 bpm')).toBeInTheDocument();
  });

  it('displays time in seconds for each zone', () => {
    render(<HRZonesCard hrZones={mockHRZones} />);
    
    expect(screen.getByText('600s')).toBeInTheDocument();
    expect(screen.getByText('900s')).toBeInTheDocument();
    expect(screen.getByText('300s')).toBeInTheDocument();
    expect(screen.getByText('150s')).toBeInTheDocument();
    expect(screen.getByText('50s')).toBeInTheDocument();
  });

  it('displays percentage with one decimal place for each zone', () => {
    render(<HRZonesCard hrZones={mockHRZones} />);
    
    expect(screen.getByText('30.0%')).toBeInTheDocument();
    expect(screen.getByText('45.0%')).toBeInTheDocument();
    expect(screen.getByText('15.0%')).toBeInTheDocument();
    expect(screen.getByText('7.5%')).toBeInTheDocument();
    expect(screen.getByText('2.5%')).toBeInTheDocument();
  });

  it('renders horizontal bar chart with 5 bars', () => {
    const { container } = render(<HRZonesCard hrZones={mockHRZones} />);
    
    const bars = container.querySelectorAll('.hr-zones-card__bar');
    expect(bars).toHaveLength(5);
  });

  it('renders bars with correct colors', () => {
    const { container } = render(<HRZonesCard hrZones={mockHRZones} />);
    
    const bars = container.querySelectorAll('.hr-zones-card__bar');
    expect(bars[0]).toHaveStyle({ backgroundColor: '#60a5fa' }); // Zone 1: light blue
    expect(bars[1]).toHaveStyle({ backgroundColor: '#34d399' }); // Zone 2: green
    expect(bars[2]).toHaveStyle({ backgroundColor: '#fbbf24' }); // Zone 3: yellow
    expect(bars[3]).toHaveStyle({ backgroundColor: '#fb923c' }); // Zone 4: orange
    expect(bars[4]).toHaveStyle({ backgroundColor: '#ef4444' }); // Zone 5: red
  });

  it('renders bars with correct widths based on percentages', () => {
    const { container } = render(<HRZonesCard hrZones={mockHRZones} />);
    
    const bars = container.querySelectorAll('.hr-zones-card__bar');
    expect(bars[0]).toHaveStyle({ width: '30%' });
    expect(bars[1]).toHaveStyle({ width: '45%' });
    expect(bars[2]).toHaveStyle({ width: '15%' });
    expect(bars[3]).toHaveStyle({ width: '7.5%' });
    expect(bars[4]).toHaveStyle({ width: '2.5%' });
  });

  it('handles zero-time zones correctly', () => {
    const zeroZoneData: HRZonesData = {
      ...mockHRZones,
      zone_5_seconds: 0,
      zone_5_percent: 0.0,
    };
    
    const { container } = render(<HRZonesCard hrZones={zeroZoneData} />);
    
    expect(screen.getByText('0s')).toBeInTheDocument();
    expect(screen.getByText('0.0%')).toBeInTheDocument();
    
    const bars = container.querySelectorAll('.hr-zones-card__bar');
    expect(bars[4]).toHaveStyle({ width: '0%' });
  });

  it('renders with accessible labels', () => {
    render(<HRZonesCard hrZones={mockHRZones} />);
    
    expect(screen.getByLabelText('Heart rate zones')).toBeInTheDocument();
    expect(screen.getByLabelText('Heart rate zones distribution')).toBeInTheDocument();
  });

  it('renders zone indicators with correct colors', () => {
    const { container } = render(<HRZonesCard hrZones={mockHRZones} />);
    
    const indicators = container.querySelectorAll('.hr-zones-card__zone-indicator');
    expect(indicators).toHaveLength(5);
    expect(indicators[0]).toHaveStyle({ backgroundColor: '#60a5fa' });
    expect(indicators[1]).toHaveStyle({ backgroundColor: '#34d399' });
    expect(indicators[2]).toHaveStyle({ backgroundColor: '#fbbf24' });
    expect(indicators[3]).toHaveStyle({ backgroundColor: '#fb923c' });
    expect(indicators[4]).toHaveStyle({ backgroundColor: '#ef4444' });
  });
});
