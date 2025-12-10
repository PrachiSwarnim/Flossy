import { useState, useEffect } from "react";
import "../styles/carousel.css";

export default function Carousel() {
  const images = [
    "/static/assets/download.jpeg",
    "/static/assets/download (1).jpeg",
    "/static/assets/download (2).jpeg",
    "/static/assets/images.jpeg",
    "/static/assets/images (1).jpeg",
    "/static/assets/images (2).jpeg",
  ];

  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % images.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="carousel">
      <div className="carousel-inner">
        <div
          className="slides"
          style={{ transform: `translateX(-${index * 100}%)` }}
        >
          {images.map((src, i) => (
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
            className={`dot ${index === i ? "active" : ""}`}
            onClick={() => setIndex(i)}
          />
        ))}
      </div>
    </div>
  );
}
