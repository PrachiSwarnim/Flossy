import { useRef } from "react";
import ServiceCard from "./ServiceCard";

export default function ServicesGrid({ services }) {
  const scrollRef = useRef(null);

  const scroll = (direction) => {
    scrollRef.current?.scrollBy({
      left: direction === "left" ? -290 : 290,
      behavior: "smooth",
    });
  };

  return (
    <div className="relative flex items-center gap-3 max-w-6xl mx-auto">
      {/* Left button */}
      <button
        onClick={() => scroll("left")}
        className="flex-shrink-0 w-10 h-10 rounded-full bg-[#1f1f1f] border border-white/10 hover:border-[#d4af37]/50 text-white/60 hover:text-[#d4af37] text-base transition-all duration-200 cursor-pointer flex items-center justify-center shadow-lg"
      >
        &#10094;
      </button>

      {/* Cards row */}
      <div
        ref={scrollRef}
        className="flex gap-5 overflow-x-auto pb-2"
        style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
      >
        {services.map((s) => (
          <ServiceCard key={s.title} {...s} />
        ))}
      </div>

      {/* Right button */}
      <button
        onClick={() => scroll("right")}
        className="flex-shrink-0 w-10 h-10 rounded-full bg-[#1f1f1f] border border-white/10 hover:border-[#d4af37]/50 text-white/60 hover:text-[#d4af37] text-base transition-all duration-200 cursor-pointer flex items-center justify-center shadow-lg"
      >
        &#10095;
      </button>
    </div>
  );
}
