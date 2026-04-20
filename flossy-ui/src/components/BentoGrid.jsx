import { motion } from "framer-motion";

const features = [
  { title: "24/7 Availability", desc: "Always here to answer your questions, day or night.", icon: "fas fa-clock" },
  { title: "Smart Booking", desc: "Effortless AI-assisted appointment scheduling.", icon: "fas fa-calendar-check" },
  { title: "Instant Answers", desc: "Get immediate dental information on demand.", icon: "fas fa-bolt" },
  { title: "Symptom Analysis", desc: "AI-driven triage to guide your next step.", icon: "fas fa-heartbeat" },
];

export default function BentoGrid() {
  return (
    <section className="bg-[#151515] py-16 px-6 md:px-[8%]">
      {/* Header */}
      <div className="text-center mb-12 max-w-2xl mx-auto">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-[2.4rem] mb-3 text-white"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          Powered by <span className="text-[#d4af37]">FlossyAI</span>
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          viewport={{ once: true }}
          className="text-white/50 text-sm leading-relaxed"
        >
          Our advanced AI assistant ensures 24/7 care, instant diagnostics, and seamless booking.
        </motion.p>
      </div>

      {/* Cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 max-w-5xl mx-auto">
        {features.map((f, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1, duration: 0.5 }}
            viewport={{ once: true }}
            whileHover={{ y: -4, scale: 1.02 }}
            className="bg-[#1f1f1f] rounded-xl p-5 border border-white/[0.06] hover:border-[#d4af37]/30 transition-all duration-300 shadow-[0_10px_30px_rgba(0,0,0,0.3)]"
          >
            <div className="text-[#d4af37] text-2xl mb-3">
              <i className={f.icon} />
            </div>
            <h3
              className="text-white text-[0.95rem] mb-1"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              {f.title}
            </h3>
            <p className="text-white/40 text-[0.8rem] leading-relaxed m-0">{f.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
