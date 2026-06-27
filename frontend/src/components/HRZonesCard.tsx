import './HRZonesCard.css';
import { HRZonesData } from '../types';

export interface HRZonesCardProps {
  /** Heart rate zones data with time, percentages, and boundaries */
  hrZones: HRZonesData | null | undefined;
}

/**
 * Zone color mapping following requirements:
 * Zone 1: light blue, Zone 2: green, Zone 3: yellow, Zone 4: orange, Zone 5: red
 */
const ZONE_COLORS = {
  1: '#60a5fa', // light blue
  2: '#34d399', // green
  3: '#fbbf24', // yellow
  4: '#fb923c', // orange
  5: '#ef4444', // red
};

/**
 * Renders heart rate zone analysis with zone list and horizontal bar chart.
 *
 * Displays:
 * - Zone list with zone number, HR range, time, percentage
 * - Horizontal bar chart with zone colors
 * - Empty state when no HR data is available
 *
 * Validates: Requirements 3.1-3.7
 */
export function HRZonesCard({ hrZones }: HRZonesCardProps) {
  // Empty state: no heart rate data available
  if (!hrZones) {
    return (
      <section className="hr-zones-card" aria-label="Heart rate zones">
        <h2 className="hr-zones-card__heading">Heart Rate Zones</h2>
        <p className="hr-zones-card__empty">
          Heart rate data was not found in your FIT file
        </p>
      </section>
    );
  }

  // Extract zone data into an array for easier iteration
  const zones = [
    {
      number: 1,
      seconds: hrZones.zone_1_seconds,
      percent: hrZones.zone_1_percent,
      bounds: hrZones.zone_boundaries[1],
    },
    {
      number: 2,
      seconds: hrZones.zone_2_seconds,
      percent: hrZones.zone_2_percent,
      bounds: hrZones.zone_boundaries[2],
    },
    {
      number: 3,
      seconds: hrZones.zone_3_seconds,
      percent: hrZones.zone_3_percent,
      bounds: hrZones.zone_boundaries[3],
    },
    {
      number: 4,
      seconds: hrZones.zone_4_seconds,
      percent: hrZones.zone_4_percent,
      bounds: hrZones.zone_boundaries[4],
    },
    {
      number: 5,
      seconds: hrZones.zone_5_seconds,
      percent: hrZones.zone_5_percent,
      bounds: hrZones.zone_boundaries[5],
    },
  ];

  return (
    <section className="hr-zones-card" aria-label="Heart rate zones">
      <h2 className="hr-zones-card__heading">Heart Rate Zones</h2>

      {/* Horizontal bar chart */}
      <div className="hr-zones-card__chart" aria-label="Heart rate zones distribution">
        {zones.map((zone) => {
          const width = zone.percent > 0 ? `${zone.percent}%` : '0%';
          return (
            <div
              key={zone.number}
              className="hr-zones-card__bar"
              style={{
                width,
                backgroundColor: ZONE_COLORS[zone.number as keyof typeof ZONE_COLORS],
              }}
              title={`Zone ${zone.number}: ${zone.percent.toFixed(1)}%`}
              aria-label={`Zone ${zone.number}: ${zone.percent.toFixed(1)}%`}
            />
          );
        })}
      </div>

      {/* Zone list */}
      <div className="hr-zones-card__list" role="list">
        {zones.map((zone) => (
          <div key={zone.number} className="hr-zones-card__item" role="listitem">
            <div className="hr-zones-card__item-header">
              <span
                className="hr-zones-card__zone-indicator"
                style={{
                  backgroundColor: ZONE_COLORS[zone.number as keyof typeof ZONE_COLORS],
                }}
                aria-hidden="true"
              />
              <span className="hr-zones-card__zone-label">
                Zone {zone.number}
              </span>
              <span className="hr-zones-card__zone-range">
                {zone.bounds[0]}-{zone.bounds[1]} bpm
              </span>
            </div>
            <div className="hr-zones-card__item-stats">
              <span className="hr-zones-card__time">{zone.seconds}s</span>
              <span className="hr-zones-card__percent">
                {zone.percent.toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
