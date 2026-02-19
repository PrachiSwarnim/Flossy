const STEPS = [
  { icon: "fas fa-laptop-medical", num: "01", title: "Online Consultation", desc: "Share your dental concerns and receive a detailed treatment plan remotely." },
  { icon: "fas fa-plane", num: "02", title: "Travel Assistance", desc: "We help coordinate your flights and accommodation for a stress-free visit." },
  { icon: "fas fa-tooth", num: "03", title: "Advanced Treatment", desc: "Receive world-class dental care using the latest modern equipment." },
  { icon: "fas fa-heart", num: "04", title: "Post-Treatment Support", desc: "Dedicated follow-up care to ensure lasting comfort after you return home." },
];

export default function TourismProcess() {
  return (
    <div className="px-6 py-12">
      <div className="text-center mb-10">
        <h3
          className="text-[1.8rem] text-white mb-2"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          A <span className="text-[#d4af37] italic">Seamless</span> Experience
        </h3>
        <p className="text-white/40 text-sm">From consultation to after-care — we handle everything.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-5xl mx-auto">
        {STEPS.map((s, i) => (
          <div
            key={i}
            className="relative bg-[#1a1a1a] rounded-xl p-6 border border-white/[0.06] hover:border-[#d4af37]/20 transition-all duration-300 overflow-hidden group"
          >
            <div
              className="absolute top-3 right-4 text-[3rem] font-black text-white/[0.04] leading-none select-none"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              {s.num}
            </div>
            <div className="w-10 h-10 rounded-lg bg-[#d4af37]/10 border border-[#d4af37]/20 flex items-center justify-center mb-4">
              <i className={`${s.icon} text-[#d4af37]`} />
            </div>
            <h4
              className="text-white text-[0.95rem] mb-2"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              {s.title}
            </h4>
            <p className="text-white/40 text-[0.8rem] leading-relaxed m-0">{s.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
