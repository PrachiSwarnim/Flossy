import { SignedIn, UserButton, useClerk } from "@clerk/clerk-react";
import { Link, useNavigate } from "react-router-dom";
import "./dashboard_header.css";

export default function Header({ openAI }) {
  const { signOut } = useClerk();
  const navigate = useNavigate();

  const handleHomeClick = async () => {
    await signOut();
    navigate("/");
  };

  return (
    <header className="sa-header">
      <div className="sa-logo">
        <img src="/static/assets/logo.png" alt="logo" />
        <span>Smile Artists</span>
      </div>

      {/* RIGHT SIDE NAVIGATION */}
      <div className="sa-nav-right">
        <nav>
          <ul>
            <li>
              <button className="nav-btn" onClick={handleHomeClick}>
                Home
              </button>
            </li>

            <li>
              <button className="nav-btn" onClick={openAI}>FlossyAI</button>
            </li>

            <li><Link to="/contact">Contact</Link></li>

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
          <UserButton afterSignOutUrl="/" />
        </SignedIn>
      </div>
    </header>
  );
}
