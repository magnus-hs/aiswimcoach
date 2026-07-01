import { useLayoutEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { StrokeBreakdownEntry } from '../api/sessionService';
import { strokeLabel } from '../utils/strokeBreakdown';
import { summarizeSets } from '../utils/groupSplits';
import { LengthSplit } from '../types';
import './ActivityCard.css';

export interface ActivityCardProps {
  sessionId: string;
  sessionDate: string;
  strokeType: string;
  totalDistanceMeters: number;
  totalTimeSeconds: number;
  averagePacePer100m: number;
  swolfScore: number;
  strokeBreakdown?: StrokeBreakdownEntry[];
  splits?: LengthSplit[];
  poolLengthMeters?: number;
}

/**
 * Format seconds into "Xm Ys" display string.
 */
export function formatTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.round(totalSeconds % 60);
  return `${minutes}m ${seconds}s`;
}

/**
 * Format pace (in seconds per 100m) into "M:SS /100m" display string.
 */
export function formatPace(paceSeconds: number): string {
  const minutes = Math.floor(paceSeconds / 60);
  const seconds = Math.round(paceSeconds % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')} /100m`;
}

/**
 * Format a date string into a readable short format.
 */
function formatDate(isoString: string): string {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return isoString;
  }
}

/**
 * Group session interval strings into rows of `perLine` items, comma-joined.
 */
function chunkSession(lines: string[], perLine: number): string[] {
  if (perLine <= 1) return lines;
  const rows: string[] = [];
  for (let i = 0; i < lines.length; i += perLine) {
    rows.push(lines.slice(i, i + perLine).join(', '));
  }
  return rows;
}

/**
 * Clickable card displaying session metrics in a Strava-inspired layout.
 * Distance is the hero metric (large bold), secondary metrics below.
 * Navigates to /activity/:id on click.
 *
 * Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
 */
export function ActivityCard({
  sessionId,
  sessionDate,
  strokeType,
  totalDistanceMeters,
  totalTimeSeconds,
  averagePacePer100m,
  swolfScore,
  strokeBreakdown,
  splits,
  poolLengthMeters,
}: ActivityCardProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/activity/${sessionId}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      navigate(`/activity/${sessionId}`);
    }
  };

  const strokeLines =
    strokeBreakdown && strokeBreakdown.length > 0
      ? strokeBreakdown.map((b) => `${Math.round(b.percent)}% ${strokeLabel(b.stroke)}`)
      : [strokeType];

  const setSummary =
    splits && splits.length > 0
      ? summarizeSets(splits, poolLengthMeters && poolLengthMeters > 0 ? poolLengthMeters : 25)
      : '';
  const sessionLines = setSummary ? setSummary.split(', ') : [];

  // Adaptive desktop session layout: prefer 1 interval per line; if the
  // content would exceed the card's natural height (driven by the left
  // snapshot column), compress to 2 then 3 intervals per line, and finally
  // enable a scrollbar while keeping 3 per line.
  const snapshotRef = useRef<HTMLDivElement>(null);
  const labelRef = useRef<HTMLSpanElement>(null);
  const linesRef = useRef<HTMLSpanElement>(null);
  const [perLine, setPerLine] = useState(1);
  const [scroll, setScroll] = useState(false);
  const [linesMaxHeight, setLinesMaxHeight] = useState<number | null>(null);

  // Reset the adaptive state whenever the session content changes.
  useLayoutEffect(() => {
    setPerLine(1);
    setScroll(false);
    setLinesMaxHeight(null);
  }, [setSummary]);

  // Reset on resize so the layout is recomputed for the new width/height.
  useLayoutEffect(() => {
    function onResize() {
      setPerLine(1);
      setScroll(false);
      setLinesMaxHeight(null);
    }
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Measure and step the layout up until the content fits (or scroll is on).
  useLayoutEffect(() => {
    if (sessionLines.length === 0) return;
    if (!window.matchMedia('(min-width: 600px)').matches) return;
    const snapshot = snapshotRef.current;
    const lines = linesRef.current;
    const label = labelRef.current;
    if (!snapshot || !lines) return;

    const avail = snapshot.offsetHeight;
    const labelH = label ? label.offsetHeight : 0;
    const linesAvail = Math.max(0, avail - labelH - 6); // 6px gap allowance
    if (avail === 0) return;

    if (lines.scrollHeight > linesAvail + 2) {
      if (perLine < 3) {
        setPerLine((p) => p + 1);
      } else if (!scroll) {
        setScroll(true);
        setLinesMaxHeight(linesAvail);
      }
    }
  });

  const desktopRows = chunkSession(sessionLines, perLine);

  return (
    <article
      className="activity-card"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`${strokeLines.join(', ')} session on ${formatDate(sessionDate)}, ${totalDistanceMeters} meters`}
    >
      <div className="activity-card__snapshot" ref={snapshotRef}>
        <span className="activity-card__date">{formatDate(sessionDate)}</span>

        <div className="activity-card__distance">
          {totalDistanceMeters}m
        </div>

        <div className="activity-card__metrics">
          <div className="activity-card__metric">
            <span className="activity-card__metric-label">Time</span>
            <span className="activity-card__metric-value">{formatTime(totalTimeSeconds)}</span>
          </div>
          <div className="activity-card__metric">
            <span className="activity-card__metric-label">Pace</span>
            <span className="activity-card__metric-value">{formatPace(averagePacePer100m)}</span>
          </div>
          <div className="activity-card__metric">
            <span className="activity-card__metric-label">SWOLF</span>
            <span className="activity-card__metric-value">{swolfScore}</span>
          </div>
        </div>
      </div>

      {sessionLines.length > 0 && (
        <>
          {/* Mobile: all intervals on one comma-separated line */}
          <div className="activity-card__session activity-card__session--mobile">
            <span className="activity-card__session-label">Session</span>
            <span className="activity-card__session-text">{setSummary}</span>
          </div>

          {/* Desktop: adaptive stacked layout */}
          <div className="activity-card__session activity-card__session--desktop">
            <span className="activity-card__session-label" ref={labelRef}>Session</span>
            <span
              className="activity-card__session-lines"
              ref={linesRef}
              style={
                scroll && linesMaxHeight != null
                  ? { maxHeight: `${linesMaxHeight}px`, overflowY: 'auto' }
                  : undefined
              }
            >
              {desktopRows.map((line, i) => (
                <span key={i} className="activity-card__session-line">{line}</span>
              ))}
            </span>
          </div>
        </>
      )}

      <span className="activity-card__stroke">
        {strokeLines.map((line, i) => (
          <span key={i} className="activity-card__stroke-line">{line}</span>
        ))}
      </span>
    </article>
  );
}
