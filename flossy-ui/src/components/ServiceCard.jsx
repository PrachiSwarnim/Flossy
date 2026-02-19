import { motion } from "framer-motion";

export default function ServiceCard({ img, title, desc }) {
  return (
    <motion.div
      whileHover={{ y: -8, scale: 1.02 }}
      transition={{ type: "spring", stiffness: 300 }}
      className="relative group flex-shrink-0 w-[260px] rounded-xl overflow-hidden bg-[#1a1a1a] border border-white/[0.06] hover:border-[#d4af37]/30 shadow-[0_10px_30px_rgba(0,0,0,0.4)] hover:shadow-[0_20px_50px_rgba(212,175,55,0.1)] transition-all duration-300 cursor-pointer"
    >
      {/* Glow on hover */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
        style={{ background: "radial-gradient(circle at center, rgba(212,175,55,0.12) 0%, transparent 70%)" }}
      />

      <div className="relative h-48 overflow-hidden">
        <img
          src={img}
          alt={title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#1a1a1a] via-black/20 to-transparent" />
      </div>

      <div className="p-5 relative z-10">
        <h3
          className="text-white text-[1rem] mb-2"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          {title}
        </h3>
        <p className="text-white/45 text-[0.8rem] leading-relaxed m-0">{desc}</p>
      </div>
    </motion.div>
  );
}
