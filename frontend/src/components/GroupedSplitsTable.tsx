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
 */
export function GroupedSplitsTable({ splits, poolLengthM }: GroupedSplitsTableProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<number>>(new Set());

  if (splits.length === 0) return null;

  const groups = groupSplits(splits, poolLengthM);

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
              expanded={expandedGroups.has(group.id)}
              onToggle={() => toggleGroup(group.id)}
            />
            {expandedGroups.has(group.id) && (
              <div className="grouped-splits__detail">
                <table className="grouped-splits__detail-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Time</th>
                      <th>Strokes</th>
                      <th>Stroke</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.splits.map((split) => (
                      <tr key={split.length_number}>
                        <td>{split.length_number}</td>
                        <td>{split.time_seconds.toFixed(1)}s</td>
                        <td>{split.strokes}</td>
                        <td>{capitalize(split.stroke)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
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
    </section>
  );
}

function GroupRow({
  group,
  expanded,
  onToggle,
}: {
  group: SplitGroup;
  expanded: boolean;
  onToggle: () => void;
}) {
  const hasMultiple = group.splits.length > 1;

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
      <span className="grouped-splits__pace">{formatTime(group.avgPacePer100m)}/100m</span>
    </div>
  );
}
