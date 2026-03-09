import { Link } from "react-router-dom";
import "../styles/role_header.css";

export default function RoleHeader() {
  return (
    <header className="role-header">
      <div className="role-header-logo flex items-center gap-2.5 flex-shrink-0" onClick={() => window.location.href="/"} style={{ cursor: "pointer", display: "flex", flexDirection: "row" }}>
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

      <Link to="/" className="role-header-home">
        Home
      </Link>
    </header>
  );
}
