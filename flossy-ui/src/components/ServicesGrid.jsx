import { useRef } from "react";
import ServiceCard from "./ServiceCard";
import "../styles/services_grid.css";

export default function ServicesGrid({ services }) {
  const scrollRef = useRef(null);

  const scroll = (direction) => {
    const { current } = scrollRef;
    if (current) {
      const scrollAmount = 350; // Approx card width + gap
      current.scrollBy({
        left: direction === "left" ? -scrollAmount : scrollAmount,
        behavior: "smooth",
      });
    }
  };

  return (
    <div className="services-carousel-container">
      <button className="carousel-btn left" onClick={() => scroll("left")}>
        &#10094;
      </button>

      <section className="services-grid" ref={scrollRef}>
        {services.map((s) => (
          <ServiceCard key={s.title} {...s} />
        ))}
      </section>

      <button className="carousel-btn right" onClick={() => scroll("right")}>
        &#10095;
      </button>
    </div>
  );
}
