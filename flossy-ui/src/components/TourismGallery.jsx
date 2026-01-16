import "../styles/tourism_gallery.css";
import { useState, useEffect } from "react";

export default function TourismGallery() {
  const images = [
    "/static/assets/patient_gallery/p9.jpg",
    "/static/assets/patient_gallery/p10.jpg",
    "/static/assets/patient_gallery/Patient1.jpg",
    "/static/assets/patient_gallery/patient2.jpg",
    "/static/assets/patient_gallery/p3.jpg",
    "/static/assets/patient_gallery/p4.jpg",
    "/static/assets/patient_gallery/p5.jpg",
    "/static/assets/patient_gallery/p6.jpg",
    "/static/assets/patient_gallery/p7.jpg",
    "/static/assets/patient_gallery/p8.jpg",
    "/static/assets/patient_gallery/p11.jpg",
    "/static/assets/patient_gallery/p12.jpg",
    "/static/assets/patient_gallery/p13.jpg",
    "/static/assets/patient_gallery/p14.jpg",
    "/static/assets/patient_gallery/p15.jpg",
    "/static/assets/patient_gallery/p16.jpg",
    "/static/assets/patient_gallery/p17.jpg",
    "/static/assets/patient_gallery/p18.jpg"
  ];

  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % images.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  const nextSlide = () => {
    setIndex((prev) => (prev + 1) % images.length);
  };

  const prevSlide = () => {
    setIndex((prev) => (prev - 1 + images.length) % images.length);
  };

  return (
    <section className="tourism-gallery">
      <h2>Patient Gallery</h2>
      <p>Real smiles, real stories — transformations crafted with precision.</p>

      <div className="gallery-container">

        {/* BLURRED BACKDROP */}
        <div className="gallery-backdrop" style={{ backgroundImage: `url("${images[index]}")` }}></div>

        <button className="gallery-arrow left" onClick={prevSlide}>
          &#10094;
        </button>

        <img src={images[index]} alt="Smile Case" key={index} className="gallery-image-main" />

        <button className="gallery-arrow right" onClick={nextSlide}>
          &#10095;
        </button>
      </div>
    </section>
  );
}
