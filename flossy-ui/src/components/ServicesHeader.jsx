import "../styles/services_header.css";

export default function ServicesHeader() {
  return (
    <header className="services-header">
      <div className="logo flex items-center gap-2.5 flex-shrink-0" onClick={() => window.location.href="/"} style={{ cursor: "pointer", display: "flex", flexDirection: "row" }}>
        <img
          src="/static/assets/logo.png"
          alt="Smile Artists"
          className="w-9 h-9 rounded-full border border-[#d4af37]/50 object-cover"
        />
        <div className="flex flex-col leading-none items-end" style={{ gap: "2px", alignItems: "flex-end" }}>
          <span
            className="text-white text-[1.4rem] font-bold"
            style={{ fontFamily: "var(--font-heading)", fontSize: "1.4rem", color: "#fff" }}
          >Smile Artists</span>
          <span
            className="text-[#d4af37] text-[0.85rem] text-right"
            style={{ fontFamily: "'Monotype Corsiva', cursive", opacity: 0.8, color: "#d4af37", fontSize: "0.85rem" }}
          >...crafting smiles</span>
        </div>
      </div>

      <nav>
        <ul>
          <li><a href="/#about">About</a></li>
          <li><a href="/#ai">FlossyAI</a></li>
          <li><a href="/contact">Contact</a></li>

          <li>
            <a href="/login">
              <button className="login-btn">Login</button>
            </a>
          </li>

          <li>
            <a href="/signup">
              <button className="signup-btn">Sign Up</button>
            </a>
          </li>
        </ul>
      </nav>
    </header>
  );
}
