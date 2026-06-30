import { useState } from 'react';
import { LengthSplit } from '../types';
import { groupSplits, formatTime, formatRest, SplitGroup } from '../utils/groupSplits';
import './GroupedSplitsTable.css';

interface GroupedSplitsTableProps {
  splits: LengthSplit[];
  poolLengthM: number;
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * Grouped splits view: shows reps as expandable rows with rest between.
 * Includes cumulative distance and optional heart rate.
 */
export function GroupedSplitsTable({ splits, poolLengthM }: GroupedSplitsTableProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<number>>(new Set());

  if (splits.length === 0) return null;

  const groups = groupSplits(splits, poolLengthM);

  // Check if any split has HR data
  const hasHR = splits.some(s => s.avg_hr != null);

  // Compute cumulative distance for each group
  let cumulativeDistance = 0;
  const groupCumulatives = groups.map((group) => {
    cumulativeDistance += group.totalDistance;
    return cumulativeDistance;
  });

  // Compute cumulative time (swim + rest) for each group
  let cumulativeTime = 0;
  const groupCumulativeTimes = groups.map((group) => {
    cumulativeTime += group.totalTime;
    if (group.restAfter != null) {
      cumulativeTime += group.restAfter;
    }
    return cumulativeTime - (group.restAfter ?? 0); // time at end of swimming, before rest
  });

  const toggleGroup = (id: number) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <section className="grouped-splits" aria-label="Grouped length splits">
      <h2 className="grouped-splits__heading">Session Structure</h2>
      <div className="grouped-splits__list">
        {groups.map((group, idx) => (
          <div key={group.id}>
            <GroupRow
              group={group}
              cumulativeDistance={groupCumulatives[idx]}
              cumulativeTime={groupCumulativeTimes[idx]}
              hasHR={hasHR}
              expanded={expandedGroups.has(group.id)}
              onToggle={() => toggleGroup(group.id)}
            />
            {expandedGroups.has(group.id) && (
              <DetailRows
                group={group}
                poolLengthM={poolLengthM}
                startCumulative={groupCumulatives[idx] - group.totalDistance}
                hasHR={hasHR}
              />
            )}
            {group.restAfter != null && idx < groups.length - 1 && (
              <div className="grouped-splits__rest" aria-label={`Rest ${formatRest(group.restAfter)}`}>
                <span className="grouped-splits__rest-line" />
                <span className="grouped-splits__rest-badge">
                  Rest {formatRest(group.restAfter)}
                </span>
                <span className="grouped-splits__rest-line" />
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="grouped-splits__session-total">
        Total: {cumulativeDistance}m
      </div>
    </section>
  );
}

function GroupRow({
  group,
  cumulativeDistance,
  cumulativeTime,
  hasHR,
  expanded,
  onToggle,
}: {
  group: SplitGroup;
  cumulativeDistance: number;
  cumulativeTime: number;
  hasHR: boolean;
  expanded: boolean;
  onToggle: () => void;
}) {
  const hasMultiple = group.splits.length > 1;

  // Calculate average HR for the group
  const hrsInGroup = group.splits.filter(s => s.avg_hr != null).map(s => s.avg_hr!);
  const avgHR = hrsInGroup.length > 0 ? Math.round(hrsInGroup.reduce((a, b) => a + b, 0) / hrsInGroup.length) : null;

  return (
    <div
      className={`grouped-splits__row ${expanded ? 'grouped-splits__row--expanded' : ''}`}
      role={hasMultiple ? 'button' : undefined}
      tabIndex={hasMultiple ? 0 : undefined}
      aria-expanded={hasMultiple ? expanded : undefined}
      onClick={hasMultiple ? onToggle : undefined}
      onKeyDown={hasMultiple ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onToggle();
        }
      } : undefined}
    >
      {hasMultiple && (
        <span className={`grouped-splits__arrow ${expanded ? 'grouped-splits__arrow--open' : ''}`}>
          ▶
        </span>
      )}
      {!hasMultiple && <span className="grouped-splits__arrow-placeholder" />}
      <span className="grouped-splits__distance">{group.totalDistance}m</span>
      <span className="grouped-splits__time">{formatTime(group.totalTime)}</span>
      <span className="grouped-splits__stroke">{capitalize(group.stroke)}</span>
      {hasHR && (
        <span className="grouped-splits__hr">
          {avgHR != null ? `${avgHR} bpm` : '—'}
        </span>
      )}
      <span className="grouped-splits__cumulative">{cumulativeDistance}m</span>
      <span className="grouped-splits__cumulative">{formatTime(cumulativeTime)}</span>
      <span className="grouped-splits__pace">{formatTime(group.avgPacePer100m)}/100m</span>
    </div>
  );
}

function DetailRows({
  group,
  poolLengthM,
  startCumulative,
  hasHR,
}: {
  group: SplitGroup;
  poolLengthM: number;
  startCumulative: number;
  hasHR: boolean;
}) {
  // Compute cumulative time within the set
  let cumTime = 0;
  const cumTimes = group.splits.map((split) => {
    cumTime += split.time_seconds;
    return cumTime;
  });

  return (
    <div className="grouped-splits__detail">
      <table className="grouped-splits__detail-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Rep #</th>
            <th>Time</th>
            <th>Cum. Time</th>
            <th>Strokes</th>
            <th>Stroke</th>
            {hasHR && <th>HR</th>}
            <th>Cum. Dist</th>
          </tr>
        </thead>
        <tbody>
          {group.splits.map((split, i) => (
            <tr key={split.length_number}>
              <td>{split.length_number}</td>
              <td>{i + 1}/{group.splits.length}</td>
              <td>{split.time_seconds.toFixed(1)}s</td>
              <td className="grouped-splits__cum-cell">{formatTime(cumTimes[i])}</td>
              <td>{split.strokes}</td>
              <td>{capitalize(split.stroke)}</td>
              {hasHR && <td>{split.avg_hr != null ? `${split.avg_hr}` : '—'}</td>}
              <td className="grouped-splits__cum-cell">{startCumulative + (i + 1) * poolLengthM}m</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
