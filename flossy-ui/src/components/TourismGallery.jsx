import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const GALLERY_IMAGES = [
  "/static/assets/patient_gallery/p10.jpg",
  "/static/assets/patient_gallery/Patient1.jpg",
  "/static/assets/patient_gallery/patient2.jpg",
  "/static/assets/patient_gallery/p3.jpg",
  "/static/assets/patient_gallery/p4.jpg",
  "/static/assets/patient_gallery/p5.jpg",
  "/static/assets/patient_gallery/p6.jpg",
  "/static/assets/patient_gallery/p7.jpg",
  "/static/assets/patient_gallery/p8.jpg",
  "/static/assets/patient_gallery/p9.jpg",
  "/static/assets/patient_gallery/p11.jpg",
  "/static/assets/patient_gallery/p12.jpg",
  "/static/assets/patient_gallery/p13.jpg",
  "/static/assets/patient_gallery/p14.jpg",
  "/static/assets/patient_gallery/p15.jpg",
  "/static/assets/patient_gallery/p16.jpg",
  "/static/assets/patient_gallery/p17.jpg",
  "/static/assets/patient_gallery/p18.jpg",
];

export default function TourismGallery() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setIndex((i) => (i + 1) % GALLERY_IMAGES.length), 5000);
    return () => clearInterval(timer);
  }, []);

  const prev = () => setIndex((p) => (p - 1 + GALLERY_IMAGES.length) % GALLERY_IMAGES.length);
  const next = () => setIndex((p) => (p + 1) % GALLERY_IMAGES.length);

  return (
    <div className="py-16 px-6">
      <div className="text-center mb-10">
        <h3
          className="text-[1.8rem] text-white mb-2"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          Patient <span className="text-[#d4af37] italic">Gallery</span>
        </h3>
        <p className="text-white/40 text-sm">Real smiles, real stories — transformations crafted with precision.</p>
      </div>

      <div className="relative max-w-3xl mx-auto h-[420px] rounded-2xl overflow-hidden border border-white/[0.06]">
        {/* Blurred backdrop */}
        <div
          className="absolute inset-0 scale-110"
          style={{
            backgroundImage: `url("${GALLERY_IMAGES[index]}")`,
            backgroundSize: "cover",
            backgroundPosition: "center",
            filter: "blur(20px) brightness(0.4)",
          }}
        />

        {/* Main image */}
        <AnimatePresence mode="wait">
          <motion.img
            key={index}
            src={GALLERY_IMAGES[index]}
            alt="Patient smile"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            transition={{ duration: 0.6 }}
            className="absolute inset-0 w-full h-full object-contain z-10"
          />
        </AnimatePresence>

        {/* Arrows */}
        <button
          onClick={prev}
          className="absolute left-4 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full flex items-center justify-center bg-black/40 backdrop-blur-sm border border-white/15 text-white/70 hover:bg-[#d4af37] hover:text-[#0f0f0f] hover:border-[#d4af37] transition-all duration-200 cursor-pointer"
        >
          <i className="fas fa-chevron-left text-sm" />
        </button>
        <button
          onClick={next}
          className="absolute right-4 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full flex items-center justify-center bg-black/40 backdrop-blur-sm border border-white/15 text-white/70 hover:bg-[#d4af37] hover:text-[#0f0f0f] hover:border-[#d4af37] transition-all duration-200 cursor-pointer"
        >
          <i className="fas fa-chevron-right text-sm" />
        </button>

        {/* Dots */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex gap-1.5">
          {GALLERY_IMAGES.map((_, i) => (
            <button
              key={i}
              onClick={() => setIndex(i)}
              className={`h-1 rounded-full border-none cursor-pointer transition-all duration-300 ${
                i === index ? "w-5 bg-[#d4af37]" : "w-1 bg-white/30"
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
