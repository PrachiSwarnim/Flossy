import { useState, useEffect, useRef } from "react";
import "../styles/carousel.css";

export default function Carousel() {
  const images = [
    "/static/assets/Smile Artists Board 2.jpg",
    "/static/assets/Clinic Exterior 3.jpg",
    "/static/assets/Clinic Outside Exterior View.jpg",
    "/static/assets/Patient Tree 2.jpg",
    "/static/assets/Patient 2.jpeg",
    "/static/assets/Clinic Exterior 2.jpg",
    "/static/assets/Smile Artists Board 1.jpg",
    "/static/assets/Clinic Exterior 4.jpg",
    "/static/assets/Clinic Exterior 1.jpg",
    "/static/assets/Patient 1.jpg",
  ];

  const [index, setIndex] = useState(0);
  const transitionRef = useRef(true);

  // Duplicate first slide for smooth loop
  const slides = [...images, images[0]];

  // Move to next slide
  const nextSlide = () => {
    if (index === slides.length - 1) return; // Prevent clicking past duplicate
    setIndex((prev) => prev + 1);
  };

  // Move to prev slide
  const prevSlide = () => {
    if (index === 0) {
      // Loop back to end(real last slide)
      transitionRef.current = false;
      setIndex(images.length); // Jump to duplicate spot? No, jump to last real image index.
      // Actually, standard loop back logic:
      // complex with the duplicate at end.
      // simpler approach for manual Nav: behave circular.
      // But we have auto-scroll mixed deeply.

      // Let's stick to simple circular for manual:
      // If at 0, goes to length-1 (which is the duplicate of 0).
      // That's confusing.

      // Let's rely on the effect to handle the snap.
      // We just decrement. If 0, we can snap to end.
      return;
    }
    setIndex((prev) => prev - 1);
  };

  // Enhanced Infinite Loop Logic
  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((prev) => prev + 1);
    }, 4000);
    return () => clearInterval(timer);
  }, [index]);

  useEffect(() => {
    // If we're at the duplicate last slide (which looks like slide 0)
    if (index === slides.length - 1) {
      setTimeout(() => {
        transitionRef.current = false; // Disable transition
        setIndex(0); // Snap to real slide 0
      }, 700); // Wait for slide animation to finish
    }
    // If we are at real slide 0 coming from duplicate, or normal move
    else if (index === 0 && transitionRef.current === false) {
      // Re-enable transition after snap
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          transitionRef.current = true;
        });
      });
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
            transition: transitionRef.current ? "transform 0.7s ease-in-out" : "none",
          }}
        >
          {slides.map((src, i) => (
            <div className="slide" key={i}>
              <div
                className="slide-backdrop"
                style={{ backgroundImage: `url("${src}")` }}
              ></div>
              <img src={src} alt={`slide-${i}`} />
            </div>
          ))}
        </div>
      </div>


    </div>
  );
}
