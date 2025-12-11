import { useState, useEffect, useRef } from "react";
import "../styles/carousel.css";

export default function Carousel() {
  const images = [
    "flossy-ui/public/static/assets/download.jpeg",
    "flossy-ui/public/static/assets/download (1).jpeg",
    "flossy-ui/public/static/assets/download (2).jpeg",
    "flossy-ui/public/static/assets/images.jpeg",
    "flossy-ui/public/static/assets/images (1).jpeg",
    "flossy-ui/public/static/assets/images (2).jpeg",
  ];

  const [index, setIndex] = useState(0);
  const transitionRef = useRef(true);

  // Duplicate first slide for smooth loop
  const slides = [...images, images[0]];

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((i) => i + 1);
    }, 4000);

    return () => clearInterval(timer);
  }, []);

  // Reset to slide 0 instantly when reaching the duplicate
  useEffect(() => {
    if (index === slides.length - 1) {
      setTimeout(() => {
        transitionRef.current = false;
        setIndex(0);
      }, 600); // match slide transition speed
    } else {
      transitionRef.current = true;
    }
  }, [index, slides.length]);

  return (
    <div className="carousel">
      <div className="carousel-inner">
        <div
          className="slides"
          style={{
            transform: `translateX(-${index * 100}%)`,
            transition: transitionRef.current ? "transform 0.7s ease" : "none",
          }}
        >
          {slides.map((src, i) => (
            <div className="slide" key={i}>
              <img src={src} alt={`slide-${i}`} />
            </div>
          ))}
        </div>
      </div>

      <div className="carousel-buttons">
        {images.map((_, i) => (
          <div
            key={i}
            className={`dot ${index % images.length === i ? "active" : ""}`}
            onClick={() => setIndex(i)}
          />
        ))}
      </div>
    </div>
  );
}
