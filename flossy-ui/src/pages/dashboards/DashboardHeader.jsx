import { SignedIn, UserButton, useClerk } from "@clerk/clerk-react";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import "./dashboard_header.css";

export default function Header({ openAI }) {
  const { signOut } = useClerk();
  const navigate = useNavigate();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen);
  const closeMenu = () => setIsMenuOpen(false);

  return (
    <>
      <header
        className="sa-header sticky top-0 z-[1000] w-full py-3 px-4 md:px-8"
        id="flossy-main-header"
      >
        <div 
          className="max-w-6xl mx-auto flex items-center justify-between h-[64px] px-5 md:px-8 rounded-xl border border-white/[0.08] bg-[#141414]/90 backdrop-blur-xl"
          style={{ boxShadow: "0 4px 30px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04)" }}
        >
          {/* LOGO */}
          <div className="sa-logo flex items-center gap-2.5 flex-shrink-0" onClick={() => navigate("/")} style={{ cursor: "pointer", display: "flex", flexDirection: "row" }}>
            <img
              src="/static/assets/logo.png"
              alt="Smile Artists"
              className="w-9 h-9 rounded-full border border-[#d4af37]/50 object-cover"
            />
            <div className="flex flex-col leading-none items-end" style={{ gap: "2px" }}>
              <span
                className="text-white text-[1.4rem] font-bold"
                style={{ fontFamily: "var(--font-heading)" }}
              >Smile Artists</span>
              <span
                className="text-[#d4af37] text-[0.85rem] text-right"
                style={{ fontFamily: "'Monotype Corsiva', cursive", opacity: 0.8 }}
              >...crafting smiles</span>
            </div>
          </div>

          {/* RIGHT SIDE NAVIGATION */}
          <div className="sa-nav-right flex items-center gap-4">
            <nav className="hidden md:flex items-center gap-2">
              <Link to="/" className="px-3.5 py-1.5 text-white/60 hover:text-white text-[0.82rem] font-medium tracking-wide rounded-lg hover:bg-white/[0.05] transition-all duration-150 no-underline">
                Home
              </Link>

              {openAI && (
                <button 
                  className="px-3.5 py-1.5 text-white/60 hover:text-white text-[0.82rem] font-medium tracking-wide rounded-lg hover:bg-white/[0.05] transition-all duration-150 no-underline bg-transparent border-none cursor-pointer"
                  onClick={openAI}
                >
                  <i className="fas fa-robot" style={{ marginRight: '8px' }}></i>
                  FlossyAI
                </button>
              )}

              <SignedIn>
                <button
                  className="px-4 py-2 bg-[#d4af37] text-[#0f0f0f] hover:brightness-110 text-[0.8rem] font-bold uppercase tracking-wider rounded-lg transition-all duration-150 cursor-pointer shadow-[0_4px_14px_rgba(212,175,55,0.3)]"
                  onClick={() => signOut(() => (window.location.href = "/"))}
                >
                  Logout
                </button>
              </SignedIn>
            </nav>

            <SignedIn>
              <div className="user-profile-wrapper flex items-center">
                <UserButton afterSignOutUrl="/" />
              </div>
            </SignedIn>

            {/* Mobile Toggle Button */}
            <button className="md:hidden w-9 h-9 flex items-center justify-center rounded-lg border border-white/10 text-white/60 hover:text-[#d4af37] hover:border-[#d4af37]/30 bg-transparent cursor-pointer transition-all duration-150" onClick={toggleMenu} aria-label="Toggle Menu">
              <i className={`fas ${isMenuOpen ? 'fa-times' : 'fa-bars'} text-sm`}></i>
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Drawer Overlay */}
      <div
        onClick={closeMenu}
        className={`fixed inset-0 bg-black/60 backdrop-blur-sm z-[1001] transition-all duration-300 ${isMenuOpen ? "opacity-100 visible" : "opacity-0 invisible"}`}
      />

      {/* Mobile Drawer */}
      <aside
        className={`fixed top-0 right-0 h-full w-72 z-[1002] flex flex-col py-6 px-5 transition-transform duration-[380ms] ease-[cubic-bezier(0.25,1,0.5,1)] ${isMenuOpen ? "translate-x-0" : "translate-x-full"}`}
        style={{ background: "#111111", boxShadow: "-8px 0 30px rgba(0,0,0,0.7)" }}
      >
        <div className="flex items-center justify-between pb-4 mb-2 border-b border-white/[0.08]">
          <div className="flex items-center gap-2">
            <img src="/static/assets/logo.png" alt="" className="w-8 h-8 rounded-full border border-[#d4af37]/40 object-cover" />
            <span className="text-white/80 text-sm font-medium">Dashboard Menu</span>
          </div>
          <button
            onClick={closeMenu}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-white/40 hover:text-white hover:bg-white/[0.06] bg-transparent border-none cursor-pointer transition-all"
          >
            <i className="fas fa-times text-sm" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto py-2" style={{ scrollbarWidth: "none" }}>
          <Link to="/" onClick={closeMenu} className="flex items-center gap-3 px-3 py-3 text-white/65 hover:text-white hover:bg-white/[0.04] rounded-lg transition-all duration-150 no-underline text-[0.95rem]">
            <i className="fas fa-home"></i> Home
          </Link>
          {openAI && (
            <button 
              onClick={() => { openAI(); closeMenu(); }} 
              className="w-full text-left flex items-center gap-3 px-3 py-3 text-white/65 hover:text-white hover:bg-white/[0.04] rounded-lg transition-all duration-150 no-underline text-[0.95rem] bg-transparent border-none cursor-pointer"
            >
              <i className="fas fa-robot"></i> FlossyAI
            </button>
          )}
        </nav>

        <div className="pt-4 border-t border-white/[0.08]">
          <SignedIn>
            <button
              className="w-full py-2.5 text-center bg-[#d4af37] text-[#0f0f0f] text-[0.82rem] font-bold uppercase tracking-wide rounded-lg hover:brightness-110 transition-all cursor-pointer shadow-[0_4px_14px_rgba(212,175,55,0.25)]"
              onClick={() => signOut(() => (window.location.href = "/"))}
            >
              <i className="fas fa-sign-out-alt mr-2"></i> Logout
            </button>
          </SignedIn>
        </div>
      </aside>
    </>
  );
}
