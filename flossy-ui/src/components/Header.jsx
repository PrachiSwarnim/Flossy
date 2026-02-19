import { useState } from "react";

const NAV_LINKS = [
  { label: "About", href: "/#about" },
  { label: "Services", href: "/#services" },
  { label: "Dental Tourism", href: "/#tourism" },
  { label: "FlossyAI", href: "/#ai" },
  { label: "Contact", href: "/#contact" },
];

export default function Header() {
  const [isOpen, setIsOpen] = useState(false);
  const close = () => setIsOpen(false);

  return (
    <>
      {/* ── TOP BAR (full width sticky) ── */}
      <div className="sticky top-0 z-[1000] w-full py-3 px-4 md:px-8">

        {/* ── Pill navbar (buildenfra style) ── */}
        <div
          className="max-w-6xl mx-auto flex items-center justify-between h-[56px] px-5 md:px-8 rounded-xl border border-white/[0.08] bg-[#141414]/90 backdrop-blur-xl"
          style={{ boxShadow: "0 4px 30px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04)" }}
        >
          {/* Logo */}
          <a href="/" className="flex items-center gap-2.5 no-underline flex-shrink-0">
            <img
              src="/static/assets/logo.png"
              alt="Smile Artists"
              className="w-9 h-9 rounded-full border border-[#d4af37]/50 object-cover"
            />
            <div className="flex flex-col leading-none">
              <span
                className="text-white text-[1rem] uppercase"
                style={{ fontFamily: "'Cooper Black', serif", letterSpacing: "1.5px" }}
              >
                Smile Artists
              </span>
              <span
                className="text-[#d4af37] text-[0.65rem] text-right"
                style={{ fontFamily: "'Monotype Corsiva', cursive" }}
              >
                ...crafting smiles
              </span>
            </div>
          </a>

          {/* Desktop nav links — centered */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map(({ label, href }) => (
              <a
                key={label}
                href={href}
                className="px-3.5 py-1.5 text-white/60 hover:text-white text-[0.82rem] font-medium tracking-wide rounded-lg hover:bg-white/[0.05] transition-all duration-150 no-underline"
              >
                {label}
              </a>
            ))}
          </nav>

          {/* Desktop right — Sign In + CTA */}
          <div className="hidden md:flex items-center gap-3">
            <a
              href="/login"
              className="text-white/60 hover:text-white text-[0.82rem] font-medium tracking-wide transition-colors duration-150 no-underline px-2"
            >
              Sign In
            </a>
            <a
              href="/#appointment"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#d4af37] text-[#0f0f0f] text-[0.8rem] font-bold uppercase tracking-wider rounded-lg hover:brightness-110 hover:-translate-y-px transition-all duration-150 no-underline shadow-[0_4px_14px_rgba(212,175,55,0.3)]"
            >
              Book Appointment
            </a>
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setIsOpen((o) => !o)}
            className="md:hidden w-9 h-9 flex items-center justify-center rounded-lg border border-white/10 text-white/60 hover:text-[#d4af37] hover:border-[#d4af37]/30 bg-transparent cursor-pointer transition-all duration-150"
            aria-label="Menu"
          >
            <i className={`fas ${isOpen ? "fa-times" : "fa-bars"} text-sm`} />
          </button>
        </div>
      </div>

      {/* ── MOBILE OVERLAY ── */}
      <div
        onClick={close}
        className={`fixed inset-0 bg-black/60 backdrop-blur-sm z-[1001] transition-all duration-300 ${
          isOpen ? "opacity-100 visible" : "opacity-0 invisible"
        }`}
      />

      {/* ── MOBILE DRAWER ── */}
      <aside
        className={`fixed top-0 right-0 h-full w-72 z-[1002] flex flex-col py-6 px-5 transition-transform duration-[380ms] ease-[cubic-bezier(0.25,1,0.5,1)] ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
        style={{ background: "#111111", boxShadow: "-8px 0 30px rgba(0,0,0,0.7)" }}
      >
        {/* Drawer header */}
        <div className="flex items-center justify-between pb-4 mb-2 border-b border-white/[0.08]">
          <div className="flex items-center gap-2">
            <img src="/static/assets/logo.png" alt="" className="w-8 h-8 rounded-full border border-[#d4af37]/40 object-cover" />
            <span className="text-white/80 text-sm font-medium">Menu</span>
          </div>
          <button
            onClick={close}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-white/40 hover:text-white hover:bg-white/[0.06] bg-transparent border-none cursor-pointer transition-all"
          >
            <i className="fas fa-times text-sm" />
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex-1 overflow-y-auto py-2" style={{ scrollbarWidth: "none" }}>
          {NAV_LINKS.map(({ label, href }) => (
            <a
              key={label}
              href={href}
              onClick={close}
              className="flex items-center gap-3 px-3 py-3 text-white/65 hover:text-white hover:bg-white/[0.04] rounded-lg transition-all duration-150 no-underline text-[0.95rem]"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              {label}
            </a>
          ))}
        </nav>

        {/* Auth */}
        <div className="pt-4 border-t border-white/[0.08] flex flex-col gap-2.5">
          <a href="/login" onClick={close} className="no-underline">
            <div className="w-full py-2.5 text-center border border-white/15 text-white/60 text-[0.82rem] font-semibold uppercase tracking-wide rounded-lg hover:border-white/30 hover:text-white transition-all cursor-pointer">
              Sign In
            </div>
          </a>
          <a href="/signup" onClick={close} className="no-underline">
            <div className="w-full py-2.5 text-center bg-[#d4af37] text-[#0f0f0f] text-[0.82rem] font-bold uppercase tracking-wide rounded-lg hover:brightness-110 transition-all cursor-pointer shadow-[0_4px_14px_rgba(212,175,55,0.25)]">
              Book Appointment
            </div>
          </a>
        </div>

        <div className="pt-3 mt-2 border-t border-white/[0.06] text-center text-[0.7rem] text-white/20">
          Powered by <strong className="text-[#d4af37]/60">FlossyAI</strong>
        </div>
      </aside>
    </>
  );
}
