import { useEffect, useState } from 'react';
import swimmerPhoto from '../assets/swimmer.jpg';
import swimmerPhoto2 from '../assets/swimmer2.jpg';
import swimmerPhoto3 from '../assets/swimmer3.jpg';
import './SwimSlider.css';

/**
 * Real swimmer photo slide.
 */
function SwimmerPhotoSlide({ src, alt }: { src: string; alt: string }) {
  return <img src={src} alt={alt} className="swim-slider__photo" />;
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
  { component: <SwimmerPhotoSlide src={swimmerPhoto} alt="A swimmer training in a pool" />, caption: 'Every stroke, tracked and understood.' },
  { component: <SwimmerPhotoSlide src={swimmerPhoto2} alt="A swimmer mid-stroke" />, caption: 'Built for lap swimmers, not just runners.' },
  { component: <SwimmerPhotoSlide src={swimmerPhoto3} alt="A swimmer pushing off the wall" />, caption: 'Real sessions. Real progress.' },
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
