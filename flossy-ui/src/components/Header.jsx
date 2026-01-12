import "../styles/header.css";

import "../styles/sidebar_footer.css";
import { useState, useRef } from "react";
import { services } from "../data/services";

export default function Header({ openAI }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const [showTopArrow, setShowTopArrow] = useState(false);
  const [showBottomArrow, setShowBottomArrow] = useState(true);

  const toggleMenu = () => setIsOpen(!isOpen);
  const closeMenu = () => setIsOpen(false);

  const handleScroll = () => {
    if (dropdownRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = dropdownRef.current;
      // Show UP arrow if we have scrolled down (scrollTop > 0)
      setShowTopArrow(scrollTop > 0);
      // Show DOWN arrow if we are NOT at the bottom
      setShowBottomArrow(Math.ceil(scrollTop + clientHeight) < scrollHeight - 5);
    }
  };

  const scrollBottom = () => {
    if (dropdownRef.current) {
      dropdownRef.current.scrollTo({
        top: dropdownRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  };

  const scrollTop = () => {
    if (dropdownRef.current) {
      dropdownRef.current.scrollTo({
        top: 0,
        behavior: "smooth"
      });
    }
  };

  return (
    <>
      <header className="header">
        <div className="logo">
          <img src="/static/assets/logo.png" alt="Smile Artists Logo" />
          <div style={{ display: "flex", flexDirection: "column", lineHeight: "0.9", alignItems: "flex-end", gap: "5px" }}>
            <span style={{ textTransform: "none" }}>Smile Artists</span>
            <span className="text-tagline" style={{ fontSize: "1.1rem", color: "#d4af37", textTransform: "none", letterSpacing: "0px" }}>...crafting smiles</span>
          </div>
        </div>

        {/* Header Actions */}
        <div className="header-actions">
          <a href="/#contact" className="header-simple-link">Contact Us</a>
          <a href="/#appointment" className="header-outline-btn">Book Appointment</a>
          <div className="hamburger" onClick={toggleMenu}>
            {isOpen ? <i className="fas fa-times"></i> : <i className="fas fa-bars"></i>}
          </div>
        </div>
      </header>

      {/* Sidebar Overlay */}
      <div className={`sidebar-overlay ${isOpen ? "open" : ""}`} onClick={closeMenu}></div>

      {/* Sidebar Drawer */}
      <aside className={`sidebar ${isOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <h3>Menu</h3>
          <button className="close-btn" onClick={closeMenu}>
            <i className="fas fa-times"></i>
          </button>
        </div>

        <nav className="sidebar-nav">
          <ul>
            <li><a href="/#about" onClick={closeMenu}>About</a></li>

            <li className="services-dropdown">
              <a href="/#services" onClick={closeMenu}>
                Our Services
              </a>

              <div className="services-list-container">
                {/* Scroll Up Arrow */}
                <div
                  className={`scroll-arrow up ${showTopArrow ? 'visible' : ''}`}
                  onClick={scrollTop}
                  style={{ opacity: showTopArrow ? 1 : 0, pointerEvents: showTopArrow ? 'auto' : 'none' }}
                >
                  <i className="fas fa-chevron-up"></i>
                </div>

                <ul className="dropdown-menu" ref={dropdownRef} onScroll={handleScroll}>
                  {services.map((s, i) => (
                    <li key={i}>
                      <a href={`/#services`} onClick={closeMenu}>{s.title}</a>
                    </li>
                  ))}
                </ul>

                {/* Scroll Down Arrow */}
                <div
                  className={`scroll-arrow down ${showBottomArrow ? 'visible' : ''}`}
                  onClick={scrollBottom}
                  style={{ opacity: showBottomArrow ? 1 : 0, pointerEvents: showBottomArrow ? 'auto' : 'none' }}
                >
                  <i className="fas fa-chevron-down"></i>
                </div>
              </div>
            </li>

            <li><a href="/#tourism" onClick={closeMenu}>Dental Tourism</a></li>
            <li><a href="/#ai" onClick={closeMenu}>FlossyAI</a></li>
            <li><a href="/#contact" onClick={closeMenu}>Contact</a></li>
          </ul>

          <div className="sidebar-actions">
            <div className="auth-item">
              <span className="auth-text">Already a user?</span>
              <a href="/login" onClick={closeMenu}>
                <button className="login-btn">Login</button>
              </a>
            </div>

            <div className="auth-item">
              <span className="auth-text">New User?</span>
              <a href="/signup" onClick={closeMenu}>
                <button className="signup-btn">Sign Up</button>
              </a>
            </div>
          </div>

          <div className="sidebar-footer">
            <span>Powered by</span>
            <strong style={{ color: "var(--primary-gold)" }}> FlossyAI</strong>
          </div>
        </nav>
      </aside>
    </>
  );
}
