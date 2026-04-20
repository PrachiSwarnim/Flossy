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
        className="sa-header"
        id="flossy-main-header"
        style={{
          width: "100%",
          maxWidth: "100%",
          height: "auto",
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          margin: 0,
          borderRadius: 0,
          zIndex: 9999,
          background: "rgba(15, 15, 15, 0.98)",
          backdropFilter: "blur(20px)",
          borderBottom: "1px solid rgba(212, 175, 55, 0.3)",
          boxSizing: "border-box",
          padding: "0.8rem 4%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          overflowX: "hidden"
        }}
      >
        <div className="sa-logo flex items-center gap-2.5 flex-shrink-0" onClick={() => navigate("/")} style={{ cursor: "pointer", display: "flex", flexDirection: "row" }}>
          <img
            src="/static/assets/logo.png"
            alt="Smile Artists"
            className="w-9 h-9 rounded-full border border-[#d4af37]/50 object-cover"
            style={{ marginTop: "-4px" }}
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
        <div className="sa-nav-right">
          <nav className="desktop-nav">
            <ul>
              <li>
                <Link to="/" className="nav-btn">Home</Link>
              </li>

              {openAI && (
                <li>
                  <button className="nav-btn" onClick={openAI}>
                    <i className="fas fa-robot" style={{ marginRight: '8px' }}></i>
                    FlossyAI
                  </button>
                </li>
              )}

              <SignedIn>
                <li>
                  <button
                    className="logout-btn"
                    onClick={() => signOut(() => (window.location.href = "/"))}
                  >
                    Logout
                  </button>
                </li>
              </SignedIn>
            </ul>
          </nav>

          <SignedIn>
            <div className="user-profile-wrapper">
              <UserButton afterSignOutUrl="/" />
            </div>
          </SignedIn>

          {/* Mobile Toggle Button */}
          <button className="mobile-menu-toggle" onClick={toggleMenu} aria-label="Toggle Menu">
            <i className={`fas ${isMenuOpen ? 'fa-times' : 'fa-bars'}`}></i>
          </button>
        </div>
      </header>

      {/* Mobile Drawer Overlay */}
      <div className={`mobile-nav-overlay ${isMenuOpen ? 'active' : ''}`} onClick={closeMenu}>
        <div className={`mobile-nav-drawer ${isMenuOpen ? 'active' : ''}`} onClick={(e) => e.stopPropagation()}>
          <div className="drawer-header">
             <span className="drawer-title">Navigation</span>
             <button onClick={closeMenu} className="drawer-close"><i className="fas fa-times"></i></button>
          </div>
          <nav className="drawer-nav">
            <Link to="/" onClick={closeMenu} className="drawer-link">
              <i className="fas fa-home"></i> Home
            </Link>
            {openAI && (
              <button onClick={() => { openAI(); closeMenu(); }} className="drawer-link btn-link">
                <i className="fas fa-robot"></i> FlossyAI
              </button>
            )}
            <SignedIn>
              <button
                className="drawer-link btn-link logout"
                onClick={() => signOut(() => (window.location.href = "/"))}
              >
                <i className="fas fa-sign-out-alt"></i> Logout
              </button>
            </SignedIn>
          </nav>
        </div>
      </div>
    </>
  );
}
