import "../styles/tourism_gallery.css";
import { useState, useEffect } from "react";

export default function TourismGallery() {
  const images = [
    "/static/assets/patient1.jpg",
    "/static/assets/patient2.jpg",
    "/static/assets/patient3.jpg",
    "/static/assets/patient4.jpg"
  ];

  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % images.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  return (
    <section className="tourism-gallery">
      <h2>Patient Gallery</h2>
      <p>Real smiles, real stories — transformations crafted with precision.</p>

      <div className="gallery-container">
        <img src={images[index]} alt="Smile Case" />
      </div>

      <div className="dots">
        {images.map((_, i) => (
          <span key={i} className={i === index ? "dot active" : "dot"}
                onClick={() => setIndex(i)}></span>
        ))}
      </div>
    </section>
  );
}
