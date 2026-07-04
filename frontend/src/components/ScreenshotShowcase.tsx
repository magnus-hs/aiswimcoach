import { useState } from 'react';
import screenshot1 from '../assets/screenshot1.png';
import screenshot2 from '../assets/screenshot2.png';
import screenshot3 from '../assets/screenshot3.png';
import screenshot4 from '../assets/screenshot4.png';
import './ScreenshotShowcase.css';

const SHOTS: { src: string; alt: string; caption: string }[] = [
  { src: screenshot1, alt: 'Session detail with interval breakdown', caption: 'Every set, every length, broken down' },
  { src: screenshot2, alt: 'Efficiency and sweet spot analysis', caption: 'Find your efficiency sweet spot' },
  { src: screenshot3, alt: 'Heart rate zones and training load', caption: 'Heart rate zones, tracked over time' },
  { src: screenshot4, alt: 'Dashboard overview with distance charts', caption: 'Your whole training picture, at a glance' },
];

/**
 * Real product screenshots displayed in a browser-frame style card grid,
 * with a lightbox to view a larger version on click.
 */
export function ScreenshotShowcase() {
  const [active, setActive] = useState<number | null>(null);

  return (
    <>
      <div className="screenshot-showcase">
        {SHOTS.map((shot, i) => (
          <button
            key={i}
            type="button"
            className="screenshot-showcase__frame"
            onClick={() => setActive(i)}
            aria-label={`View larger: ${shot.caption}`}
          >
            <span className="screenshot-showcase__chrome">
              <span className="screenshot-showcase__dot" />
              <span className="screenshot-showcase__dot" />
              <span className="screenshot-showcase__dot" />
            </span>
            <img src={shot.src} alt={shot.alt} className="screenshot-showcase__img" loading="lazy" />
            <span className="screenshot-showcase__caption">{shot.caption}</span>
          </button>
        ))}
      </div>

      {active !== null && (
        <div
          className="screenshot-showcase__lightbox"
          role="dialog"
          aria-modal="true"
          aria-label={SHOTS[active].caption}
          onClick={() => setActive(null)}
        >
          <img src={SHOTS[active].src} alt={SHOTS[active].alt} className="screenshot-showcase__lightbox-img" />
          <button
            type="button"
            className="screenshot-showcase__lightbox-close"
            onClick={() => setActive(null)}
            aria-label="Close"
          >
            ×
          </button>
        </div>
      )}
    </>
  );
}
