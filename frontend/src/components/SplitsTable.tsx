import { LengthSplit } from '../types';

interface SplitsTableProps {
  splits: LengthSplit[];
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * Compact table showing per-length split times with alternating row colors.
 */
export function SplitsTable({ splits }: SplitsTableProps) {
  if (splits.length === 0) return null;

  return (
    <section className="splits-table" aria-label="Length splits">
      <h2 className="splits-table__heading">Length Splits</h2>
      <div className="splits-table__wrapper">
        <table className="splits-table__table">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Time (s)</th>
              <th scope="col">Strokes</th>
              <th scope="col">Stroke</th>
            </tr>
          </thead>
          <tbody>
            {splits.map((split) => (
              <tr key={split.length_number}>
                <td>{split.length_number}</td>
                <td>{split.time_seconds.toFixed(1)}</td>
                <td>{split.strokes}</td>
                <td>{capitalize(split.stroke)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
