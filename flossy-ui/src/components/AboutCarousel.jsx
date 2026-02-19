import { useState, useEffect, useRef } from "react";

export default function AboutCarousel() {
  const images = [
    "/static/assets/Clinic Interior 4.jpg",
    "/static/assets/Clinic Interior 2.jpg",
    "/static/assets/Clinic Interior 3.jpg",
    "/static/assets/Clinic Interior 1.jpg",
    "/static/assets/Clinic Interior 5.jpg",
  ];

  const [index, setIndex] = useState(0);
  const transitionRef = useRef(true);
  const slides = [...images, images[0]];

  useEffect(() => {
    const timer = setInterval(() => setIndex((p) => p + 1), 4000);
    return () => clearInterval(timer);
  }, [index]);

  useEffect(() => {
    if (index === slides.length - 1) {
      setTimeout(() => { transitionRef.current = false; setIndex(0); }, 700);
    } else if (index === 0 && transitionRef.current === false) {
      requestAnimationFrame(() => requestAnimationFrame(() => { transitionRef.current = true; }));
    } else {
      transitionRef.current = true;
    }
  }, [index, slides.length]);

  return (
    <div className="relative w-full h-full overflow-hidden rounded-2xl">
      {/* Slides */}
      <div
        className="flex h-full"
        style={{
          transform: `translateX(-${index * 100}%)`,
          transition: transitionRef.current ? "transform 0.7s ease-in-out" : "none",
        }}
      >
        {slides.map((src, i) => (
          <div key={i} className="relative flex-shrink-0 w-full h-full bg-black">
            <div
              className="absolute inset-0 scale-110"
              style={{
                backgroundImage: `url("${src}")`,
                backgroundSize: "cover",
                backgroundPosition: "center",
                filter: "blur(20px) brightness(0.4)",
              }}
            />
            <img
              src={src}
              alt={`clinic-interior-${i}`}
              className="relative z-10 w-full h-full object-cover"
            />
          </div>
        ))}
      </div>

      {/* Arrows */}
      <button
        onClick={() => setIndex((i) => i === 0 ? images.length - 1 : i - 1)}
        className="absolute left-3 top-1/2 -translate-y-1/2 z-20 w-9 h-9 rounded-full flex items-center justify-center bg-black/40 backdrop-blur-sm border border-white/20 text-white text-sm hover:bg-[#d4af37]/80 transition-all duration-200 cursor-pointer"
      >
        <i className="fas fa-chevron-left" />
      </button>
      <button
        onClick={() => setIndex((i) => i + 1)}
        className="absolute right-3 top-1/2 -translate-y-1/2 z-20 w-9 h-9 rounded-full flex items-center justify-center bg-black/40 backdrop-blur-sm border border-white/20 text-white text-sm hover:bg-[#d4af37]/80 transition-all duration-200 cursor-pointer"
      >
        <i className="fas fa-chevron-right" />
      </button>

      {/* Dots */}
      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-20 flex gap-1.5">
        {images.map((_, i) => (
          <button
            key={i}
            onClick={() => setIndex(i)}
            className={`h-1.5 rounded-full transition-all duration-300 border-none cursor-pointer ${
              i === index % images.length ? "bg-[#d4af37] w-4" : "bg-white/40 w-1.5"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
