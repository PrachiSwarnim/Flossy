import { SignedIn, UserButton, useClerk } from "@clerk/clerk-react";
import { Link, useNavigate } from "react-router-dom";
import "./dashboard_header.css";

export default function Header({ openAI }) {
  const { signOut } = useClerk();
  const navigate = useNavigate();

  return (
    <header className="sa-header" id="flossy-main-header">
      <div className="sa-logo" onClick={() => navigate("/")} style={{ cursor: "pointer" }}>
        <img src="/static/assets/logo.png" alt="logo" />
        <div style={{ display: "flex", flexDirection: "column", lineHeight: "1", alignItems: "flex-start", gap: "2px" }}>
          <span className="text-brand" style={{ fontSize: "1.4rem", color: "#d4af37", fontWeight: "700" }}>Smile Artists</span>
          <span className="text-tagline" style={{ fontSize: "0.85rem", color: "#d4af37", opacity: 0.8, fontWeight: "normal" }}>...crafting smiles</span>
        </div>
      </div>

      {/* RIGHT SIDE NAVIGATION */}
      <div className="sa-nav-right">
        <nav>
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
      </div>
    </header>
  );
}
