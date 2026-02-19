import { motion } from "framer-motion";

const contacts = [
  {
    icon: "fas fa-phone-alt",
    title: "Call Us",
    lines: ["+91-8507-213-999", "+91-9693-288-488"],
  },
  {
    icon: "fas fa-envelope",
    title: "Email Us",
    lines: ["info@smileartists.in", "www.smileartists.in"],
  },
  {
    icon: "fas fa-map-marker-alt",
    title: "Visit Us",
    lines: [
      "573, Smile Artists Dental Studio",
      "Artemis Hospital Road, Koyal Vihar",
      "Gurugram – 122003, Haryana, India",
    ],
    extra: "10:30 AM – 8:30 PM (Mon–Sun)",
  },
];

export default function ContactSection() {
  return (
    <section className="bg-[#151515] py-16 px-6 md:px-[8%]">
      {/* Heading */}
      <div className="text-center mb-12">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-[2.2rem] text-white"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          Contact <span className="text-[#d4af37]">Us</span>
        </motion.h2>
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto mb-12">
        {contacts.map((c, i) => (
          <motion.div
            key={c.title}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1, duration: 0.5 }}
            viewport={{ once: true }}
            className="bg-[#1a1a1a] rounded-2xl p-6 border border-white/[0.06] hover:border-[#d4af37]/25 transition-all duration-300 shadow-[0_10px_40px_rgba(0,0,0,0.3)] flex gap-4"
          >
            {/* Icon */}
            <div className="flex-shrink-0 w-11 h-11 rounded-xl bg-[#d4af37]/10 border border-[#d4af37]/20 flex items-center justify-center text-[#d4af37] text-lg mt-0.5">
              <i className={c.icon} />
            </div>

            {/* Content */}
            <div>
              <h3
                className="text-white text-base mb-2"
                style={{ fontFamily: "'Playfair Display', serif" }}
              >
                {c.title}
              </h3>
              {c.lines.map((l, j) => (
                <p key={j} className="text-white/50 text-sm leading-relaxed m-0">{l}</p>
              ))}
              {c.extra && (
                <p className="text-[#d4af37]/70 text-xs mt-2 flex items-center gap-1.5 m-0">
                  <i className="far fa-clock" />
                  {c.extra}
                </p>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Map */}
      <div className="max-w-5xl mx-auto rounded-2xl overflow-hidden border border-white/[0.06] shadow-[0_10px_40px_rgba(0,0,0,0.4)]">
        <iframe
          title="Google Map Location"
          src="https://maps.google.com/maps?q=573,+Smile+Artists+Dental+Studio,+Artemis+Hospital+Road,+Koyal+Vihar,+Gurugram&t=&z=15&ie=UTF8&iwloc=&output=embed"
          width="100%"
          height="400"
          style={{ border: 0, display: "block" }}
          allowFullScreen=""
          loading="lazy"
        />
      </div>
    </section>
  );
}
