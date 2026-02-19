import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";

const IMAGES = [
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

export default function Carousel() {
  const [index, setIndex] = useState(0);
  const timerRef = useRef(null);

  const resetTimer = () => {
    clearInterval(timerRef.current);
    timerRef.current = setInterval(() => setIndex((p) => (p + 1) % IMAGES.length), 5000);
  };

  useEffect(() => {
    resetTimer();
    return () => clearInterval(timerRef.current);
  }, []);

  const goTo = (i) => { setIndex(i); resetTimer(); };
  const prev = () => { setIndex((p) => (p - 1 + IMAGES.length) % IMAGES.length); resetTimer(); };
  const next = () => { setIndex((p) => (p + 1) % IMAGES.length); resetTimer(); };

  return (
    <div
      className="relative w-full overflow-hidden"
      style={{ height: "calc(100vh - 80px)", minHeight: "520px" }}
    >
      {/* Background image crossfade */}
      <AnimatePresence initial={false}>
        <motion.div
          key={index}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.9 }}
          className="absolute inset-0"
          style={{
            backgroundImage: `url("${IMAGES[index]}")`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
      </AnimatePresence>

      {/* Dark overlay */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(to bottom, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.45) 40%, rgba(0,0,0,0.78) 100%)",
        }}
      />

      {/* Grid dot pattern */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.06) 1px, transparent 1px)",
          backgroundSize: "36px 36px",
        }}
      />

      {/* Radial glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse at 50% 60%, rgba(212,175,55,0.07) 0%, transparent 60%)",
        }}
      />

      {/* Hero content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center z-10">
        <motion.span
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.6 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-[0.7rem] font-semibold uppercase tracking-widest text-[#d4af37] bg-[#d4af37]/10 border border-[#d4af37]/25 mb-6"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[#d4af37] animate-pulse" />
          Gurugram&apos;s #1 Dental Studio
        </motion.span>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.7 }}
          className="text-[2.8rem] sm:text-[3.8rem] md:text-[4.8rem] text-white leading-tight max-w-4xl mb-4"
          style={{ fontFamily: "'Playfair Display', serif", letterSpacing: "-0.01em" }}
        >
          World-Class Dental Care,{" "}
          <span className="text-[#d4af37] italic">Crafted for You</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45, duration: 0.6 }}
          className="text-white/65 text-[1rem] md:text-[1.1rem] max-w-xl mb-8 leading-relaxed"
        >
          Advanced dentistry, AI-assisted booking, and a team that truly cares — all under one roof in Gurugram.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.6 }}
          className="flex flex-col sm:flex-row gap-4 mb-10"
        >
          <Link
            to="/signup"
            className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-[#d4af37] text-[#0f0f0f] font-bold text-[0.9rem] uppercase tracking-wider rounded-sm hover:brightness-110 hover:-translate-y-0.5 transition-all duration-200 no-underline shadow-[0_8px_30px_rgba(212,175,55,0.3)]"
          >
            Book Appointment <i className="fas fa-arrow-right text-xs" />
          </Link>
          <a
            href="#about"
            className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-white/10 backdrop-blur-sm border border-white/25 text-white font-semibold text-[0.9rem] uppercase tracking-wider rounded-sm hover:bg-white/15 hover:border-white/40 transition-all duration-200 no-underline"
          >
            Learn More
          </a>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.6 }}
          className="text-white/40 text-[0.8rem]"
        >
          Trusted by{" "}
          <span className="text-[#d4af37] font-semibold">10,000+ patients</span>{" "}
          across India &amp; internationally
        </motion.p>
      </div>

      {/* Arrows */}
      <button
        onClick={prev}
        className="absolute left-5 top-1/2 -translate-y-1/2 z-20 w-11 h-11 rounded-full flex items-center justify-center bg-black/30 backdrop-blur-sm border border-white/15 text-white/70 hover:bg-[#d4af37] hover:text-[#0f0f0f] hover:border-[#d4af37] hover:scale-110 transition-all duration-200 cursor-pointer"
        aria-label="Previous"
      >
        <i className="fas fa-chevron-left text-sm" />
      </button>
      <button
        onClick={next}
        className="absolute right-5 top-1/2 -translate-y-1/2 z-20 w-11 h-11 rounded-full flex items-center justify-center bg-black/30 backdrop-blur-sm border border-white/15 text-white/70 hover:bg-[#d4af37] hover:text-[#0f0f0f] hover:border-[#d4af37] hover:scale-110 transition-all duration-200 cursor-pointer"
        aria-label="Next"
      >
        <i className="fas fa-chevron-right text-sm" />
      </button>

      {/* Dots */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex gap-2">
        {IMAGES.map((_, i) => (
          <button
            key={i}
            onClick={() => goTo(i)}
            aria-label={`Slide ${i + 1}`}
            className={`h-1.5 rounded-full transition-all duration-300 border-none cursor-pointer ${i === index ? "w-7 bg-[#d4af37]" : "w-1.5 bg-white/30 hover:bg-white/60"}`}
          />
        ))}
      </div>
    </div>
  );
}
