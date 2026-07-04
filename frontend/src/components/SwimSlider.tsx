import { useEffect, useState } from 'react';
import './SwimSlider.css';

/**
 * A swimmer mid-stroke in a lane, viewed from above.
 */
function SwimmerSlide() {
  return (
    <svg viewBox="0 0 400 240" className="swim-slider__art" role="img" aria-label="Swimmer in a pool lane">
      <defs>
        <linearGradient id="water1" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(205, 70%, 22%)" />
          <stop offset="100%" stopColor="hsl(205, 75%, 14%)" />
        </linearGradient>
      </defs>
      <rect width="400" height="240" fill="url(#water1)" />
      {/* Lane lines */}
      {[40, 90, 150, 210].map((y) => (
        <line key={y} x1="0" y1={y} x2="400" y2={y} stroke="hsl(45, 90%, 55%)" strokeWidth="3" strokeDasharray="18 14" opacity="0.55" />
      ))}
      {/* Ripples */}
      <g stroke="rgba(255,255,255,0.18)" strokeWidth="2" fill="none">
        <path d="M20 190 q20 -8 40 0 t40 0 t40 0" />
        <path d="M240 60 q20 -6 40 0 t40 0" />
      </g>
      {/* Swimmer body (front-crawl, top-down) */}
      <g transform="translate(140,120) rotate(-6)">
        <ellipse cx="0" cy="0" rx="58" ry="14" fill="hsl(210, 90%, 60%)" />
        <circle cx="62" cy="-2" r="12" fill="hsl(28, 60%, 62%)" />
        {/* Extended arm */}
        <path d="M15 -8 Q55 -30 95 -18" stroke="hsl(28, 60%, 62%)" strokeWidth="9" strokeLinecap="round" fill="none" />
        {/* Trailing arm */}
        <path d="M-20 6 Q-45 26 -60 14" stroke="hsl(28, 60%, 62%)" strokeWidth="9" strokeLinecap="round" fill="none" />
        {/* Legs / kick */}
        <path d="M-58 0 Q-80 -14 -100 -4" stroke="hsl(210, 90%, 60%)" strokeWidth="10" strokeLinecap="round" fill="none" />
        <path d="M-58 4 Q-82 18 -102 20" stroke="hsl(210, 80%, 50%)" strokeWidth="10" strokeLinecap="round" fill="none" />
      </g>
      {/* Splash */}
      <g fill="rgba(255,255,255,0.5)">
        <circle cx="238" cy="98" r="3" />
        <circle cx="248" cy="106" r="2" />
        <circle cx="228" cy="108" r="2.5" />
        <circle cx="38" cy="132" r="2" />
        <circle cx="30" cy="140" r="2.5" />
      </g>
    </svg>
  );
}

/**
 * A pool viewed from the side with underwater lane markers — evokes lap swimming.
 */
function PoolLanesSlide() {
  return (
    <svg viewBox="0 0 400 240" className="swim-slider__art" role="img" aria-label="Swimming pool lanes">
      <defs>
        <linearGradient id="water2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(205, 75%, 26%)" />
          <stop offset="100%" stopColor="hsl(205, 80%, 10%)" />
        </linearGradient>
      </defs>
      <rect width="400" height="240" fill="url(#water2)" />
      {/* Perspective lane lines converging */}
      <g stroke="rgba(255,255,255,0.25)" strokeWidth="2">
        <line x1="0" y1="30" x2="400" y2="10" />
        <line x1="0" y1="80" x2="400" y2="70" />
        <line x1="0" y1="130" x2="400" y2="130" />
        <line x1="0" y1="180" x2="400" y2="190" />
        <line x1="0" y1="230" x2="400" y2="250" />
      </g>
      {/* Floating lane rope with buoys */}
      <g>
        <line x1="0" y1="105" x2="400" y2="100" stroke="hsl(45, 90%, 55%)" strokeWidth="3" opacity="0.8" />
        {[20, 70, 120, 170, 220, 270, 320, 370].map((x, i) => (
          <circle key={x} cx={x} cy={101 - (i % 2)} r="8" fill={i % 2 === 0 ? 'hsl(45, 90%, 55%)' : 'hsl(210, 90%, 60%)'} />
        ))}
      </g>
      {/* Sunlight glints */}
      <g fill="rgba(255,255,255,0.35)">
        <ellipse cx="90" cy="55" rx="22" ry="4" />
        <ellipse cx="280" cy="150" rx="30" ry="5" />
        <ellipse cx="180" cy="200" rx="18" ry="3" />
      </g>
      {/* Distant swimmer silhouette */}
      <g transform="translate(300,60) scale(0.6) rotate(4)">
        <ellipse cx="0" cy="0" rx="50" ry="12" fill="hsl(210, 85%, 55%)" opacity="0.9" />
        <circle cx="54" cy="-2" r="10" fill="hsl(28, 55%, 58%)" opacity="0.9" />
      </g>
    </svg>
  );
}

/**
 * Data-overlay slide — a swimmer silhouette with a stats readout, tying the visual to the product.
 */
function StatsOverlaySlide() {
  return (
    <svg viewBox="0 0 400 240" className="swim-slider__art" role="img" aria-label="Swim analytics overlay">
      <defs>
        <linearGradient id="water3" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(205, 70%, 20%)" />
          <stop offset="100%" stopColor="hsl(205, 75%, 12%)" />
        </linearGradient>
      </defs>
      <rect width="400" height="240" fill="url(#water3)" />
      {[50, 110, 170, 230].map((y) => (
        <line key={y} x1="0" y1={y} x2="400" y2={y} stroke="hsl(45, 90%, 55%)" strokeWidth="2.5" strokeDasharray="16 12" opacity="0.4" />
      ))}
      {/* Swimmer */}
      <g transform="translate(120,140) rotate(-4)">
        <ellipse cx="0" cy="0" rx="55" ry="13" fill="hsl(210, 90%, 60%)" />
        <circle cx="58" cy="-2" r="11" fill="hsl(28, 60%, 62%)" />
        <path d="M12 -8 Q50 -28 88 -16" stroke="hsl(28, 60%, 62%)" strokeWidth="8" strokeLinecap="round" fill="none" />
        <path d="M-55 0 Q-76 -12 -95 -2" stroke="hsl(210, 85%, 55%)" strokeWidth="9" strokeLinecap="round" fill="none" />
      </g>
      {/* Simple pace line chart */}
      <polyline
        points="230,190 260,170 290,178 320,150 350,140"
        fill="none"
        stroke="hsl(45, 95%, 55%)"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <g fill="hsl(45, 95%, 55%)">
        <circle cx="230" cy="190" r="3.5" />
        <circle cx="260" cy="170" r="3.5" />
        <circle cx="290" cy="178" r="3.5" />
        <circle cx="320" cy="150" r="3.5" />
        <circle cx="350" cy="140" r="3.5" />
      </g>
      {/* Stat readout card */}
      <g transform="translate(230,40)">
        <rect width="140" height="58" rx="8" fill="hsl(220, 15%, 14%)" stroke="hsl(220, 12%, 30%)" opacity="0.92" />
        <text x="12" y="22" fontSize="11" fill="hsl(220, 6%, 60%)" fontFamily="Inter, sans-serif">PACE /100m</text>
        <text x="12" y="44" fontSize="20" fontWeight="700" fill="hsl(210, 90%, 65%)" fontFamily="Inter, sans-serif">1:32</text>
      </g>
    </svg>
  );
}

const SLIDES = [
  { component: <SwimmerSlide />, caption: 'Every stroke, tracked and understood.' },
  { component: <PoolLanesSlide />, caption: 'Built for lap swimmers, not just runners.' },
  { component: <StatsOverlaySlide />, caption: 'Your data, turned into real coaching.' },
];

/**
 * Auto-advancing visual slider for the landing page hero — custom SVG illustrations
 * of a swimmer in a pool (no stock imagery), with dot navigation and captions.
 */
export function SwimSlider() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex((i) => (i + 1) % SLIDES.length);
    }, 4500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="swim-slider" aria-roledescription="carousel">
      <div className="swim-slider__viewport">
        {SLIDES.map((slide, i) => (
          <div
            key={i}
            className={`swim-slider__slide ${i === index ? 'swim-slider__slide--active' : ''}`}
            aria-hidden={i !== index}
          >
            {slide.component}
          </div>
        ))}
        <p className="swim-slider__caption">{SLIDES[index].caption}</p>
      </div>
      <div className="swim-slider__dots" role="tablist">
        {SLIDES.map((_, i) => (
          <button
            key={i}
            type="button"
            role="tab"
            aria-selected={i === index}
            aria-label={`Show slide ${i + 1}`}
            className={`swim-slider__dot ${i === index ? 'swim-slider__dot--active' : ''}`}
            onClick={() => setIndex(i)}
          />
        ))}
      </div>
    </div>
  );
}
