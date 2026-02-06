import { Link } from "react-router-dom";
import "../styles/role_header.css";

export default function RoleHeader() {
  return (
    <header className="role-header">
      <div className="role-header-logo">
        <img src="/static/assets/logo.png" alt="Smile Artists" />
        <div style={{ display: "flex", flexDirection: "column", lineHeight: "0.9", alignItems: "flex-start", gap: "3px" }}>
          <span style={{ fontSize: "1.3rem", color: "#d4af37", fontWeight: "600" }}>Smile Artists</span>
          <span style={{ fontSize: "0.85rem", color: "#d4af37", opacity: 0.8 }}>...crafting smiles</span>
        </div>
      </div>

      <Link to="/" className="role-header-home">
        Home
      </Link>
    </header>
  );
}
