import { useState } from 'react';
import { LengthSplit } from '../types';
import { groupSplits, SplitGroup } from '../utils/groupSplits';
import './TrainingLoadChart.css';

interface TrainingLoadChartProps {
  splits: LengthSplit[];
  poolLengthM: number;
  cssPace: number | null;
}

type EnergySystem = 'sprint' | 'threshold' | 'aerobic';

interface SetAnalysis {
  group: SplitGroup;
  energySystem: EnergySystem;
  intensityFactor: number;
  restMultiplier: number;
  setLoad: number;
  pace: number;
}

const ENERGY_COLORS: Record<EnergySystem, string> = {
  sprint: '#ef4444',
  threshold: '#f59e0b',
  aerobic: '#34d399',
};

const ENERGY_LABELS: Record<EnergySystem, string> = {
  sprint: 'Sprint',
  threshold: 'Threshold',
  aerobic: 'Aerobic',
};

function categorize(pace: number, css: number): EnergySystem {
  if (pace < css - 5) return 'sprint';
  if (pace > css + 5) return 'aerobic';
  return 'threshold';
}

function computeRestMultiplier(totalTime: number, restAfter: number | null): number {
  if (!restAfter || restAfter <= 0) return 1.5;
  const workToRest = totalTime / restAfter;
  return Math.min(1.5, 0.8 + workToRest * 0.2);
}

function formatPace(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function TrainingLoadChart({ splits, poolLengthM, cssPace }: TrainingLoadChartProps) {
  const [showSets, setShowSets] = useState(false);

  if (!cssPace || splits.length === 0) return null;

  const groups = groupSplits(splits, poolLengthM);
  if (groups.length === 0) return null;

  const analysis: SetAnalysis[] = groups.map(group => {
    const pace = group.avgPacePer100m;
    const energySystem = categorize(pace, cssPace);
    const intensityFactor = energySystem === 'sprint' ? 1.5 : energySystem === 'threshold' ? 1.0 : 0.7;
    const restMultiplier = computeRestMultiplier(group.totalTime, group.restAfter);
    const baseLoad = (group.totalDistance / 100) * intensityFactor;
    const setLoad = Math.round(baseLoad * restMultiplier * 10) / 10;
    return { group, energySystem, intensityFactor, restMultiplier, setLoad, pace };
  });

  const sessionLoad = Math.round(analysis.reduce((sum, a) => sum + a.setLoad, 0));
  const sprintLoad = Math.round(analysis.filter(a => a.energySystem === 'sprint').reduce((sum, a) => sum + a.setLoad, 0));
  const thresholdLoad = Math.round(analysis.filter(a => a.energySystem === 'threshold').reduce((sum, a) => sum + a.setLoad, 0));
  const aerobicLoad = Math.round(analysis.filter(a => a.energySystem === 'aerobic').reduce((sum, a) => sum + a.setLoad, 0));

  return (
    <section className="training-load" aria-label="Training load analysis">
      <h2 className="training-load__heading">Training Load Analysis</h2>
      <p className="training-load__css-ref">CSS pace: {formatPace(cssPace)} /100m</p>

      <div className="training-load__summary">
        <div className="training-load__total">
          <span className="training-load__total-value">{sessionLoad}</span>
          <span className="training-load__total-label">Session Load</span>
        </div>
        <div className="training-load__breakdown">
          <span className="training-load__breakdown-item" style={{ color: ENERGY_COLORS.sprint }}>
            Sprint: {sprintLoad}
          </span>
          <span className="training-load__breakdown-item" style={{ color: ENERGY_COLORS.threshold }}>
            Threshold: {thresholdLoad}
          </span>
          <span className="training-load__breakdown-item" style={{ color: ENERGY_COLORS.aerobic }}>
            Aerobic: {aerobicLoad}
          </span>
        </div>
      </div>

      <button
        className="training-load__expand-btn"
        onClick={() => setShowSets(!showSets)}
        aria-expanded={showSets}
      >
        <span className={`training-load__expand-arrow ${showSets ? 'training-load__expand-arrow--open' : ''}`}>▶</span>
        {showSets ? 'Hide' : 'Show'} per-set breakdown ({analysis.length} sets)
      </button>

      {showSets && (
        <div className="training-load__sets">
          <table className="training-load__table">
            <thead>
              <tr>
                <th>Set</th>
                <th>Distance</th>
                <th>Pace</th>
                <th>vs CSS</th>
                <th>Zone</th>
                <th>Load</th>
              </tr>
            </thead>
            <tbody>
              {analysis.map((a, idx) => {
                const diff = a.pace - cssPace;
                const diffLabel = diff > 0 ? `+${diff.toFixed(0)}s` : `${diff.toFixed(0)}s`;
                return (
                  <tr key={idx}>
                    <td>{idx + 1}</td>
                    <td>{a.group.totalDistance}m</td>
                    <td>{formatPace(a.pace)}</td>
                    <td className={`training-load__diff training-load__diff--${a.energySystem}`}>
                      {diffLabel}
                    </td>
                    <td>
                      <span
                        className="training-load__zone-badge"
                        style={{ background: ENERGY_COLORS[a.energySystem] }}
                      >
                        {ENERGY_LABELS[a.energySystem]}
                      </span>
                    </td>
                    <td className="training-load__load-value">{a.setLoad}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
