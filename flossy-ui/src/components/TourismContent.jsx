export default function TourismContent() {
  return (
    <div className="px-6 py-10 max-w-5xl mx-auto space-y-14">
      {/* Row 1 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
        <div>
          <h3
            className="text-[1.7rem] text-white mb-3 leading-tight"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            Our <span className="text-[#d4af37] italic">Tourism Process</span>
          </h3>
          <p className="text-white/50 text-[0.9rem] leading-relaxed">
            Our dental tourism process is designed for your comfort and convenience.
            From your first online consultation to post-treatment follow-up, our team assists you at every single step.
          </p>
        </div>
        <div className="rounded-2xl overflow-hidden border border-white/[0.06] shadow-[0_10px_40px_rgba(0,0,0,0.4)]">
          <img
            src="/static/assets/DT Process.avif"
            alt="Dental Tourism Process"
            className="w-full h-auto object-cover"
          />
        </div>
      </div>

      {/* Row 2 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
        <div className="order-2 md:order-1 rounded-2xl overflow-hidden border border-white/[0.06] shadow-[0_10px_40px_rgba(0,0,0,0.4)]">
          <img
            src="/static/assets/78a8b0_b8a8ee3e87024a1694fc9f0fc2448c22~mv2.avif"
            alt="Dental Tourism Services"
            className="w-full h-auto object-cover"
          />
        </div>
        <div className="order-1 md:order-2">
          <h3
            className="text-[1.7rem] text-white mb-3 leading-tight"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            Our <span className="text-[#d4af37] italic">Tourism Services</span>
          </h3>
          <p className="text-white/50 text-[0.9rem] leading-relaxed">
            We offer a full range of dental services for international patients — general dentistry,
            orthodontics, cosmetic treatments, implants, and full-mouth rehabilitation — using cutting-edge technology.
          </p>
        </div>
      </div>
    </div>
  );
}
