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

const SLIDES = [
  { component: <SwimmerPhotoSlide src={swimmerPhoto} alt="A swimmer training in a pool" />, caption: 'Every stroke, tracked and understood.' },
  { component: <SwimmerPhotoSlide src={swimmerPhoto2} alt="A swimmer mid-stroke" />, caption: 'Built for lap and open water swimmers.' },
  { component: <SwimmerPhotoSlide src={swimmerPhoto3} alt="A swimmer pushing off the wall" />, caption: 'Real sessions. Real progress.' },
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
