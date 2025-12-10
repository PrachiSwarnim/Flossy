import { Link } from "react-router-dom";
import "../styles/header.css";

export default function Header() {
  return (
    <header className="sa-header">
      {/* LOGO */}
      <div className="sa-logo">
        <img src="/static/assets/logo.avif" alt="Smile Artists Logo" />
        <span>Smile Artists</span>
      </div>

      {/* NAVIGATION */}
      <nav>
        <ul>
          <li><a href="#about">About</a></li>
          <li><a href="#ai">FlossyAI</a></li>
          <li><Link to="/services">Our Services</Link></li>
          <li><Link to="/dental_tourism">Dental Tourism</Link></li>
          <li><Link to="/contact">Contact</Link></li>

          {/* ALWAYS show Login + Signup on the main website */}
          <li><Link className="login-btn" to="/login">Login</Link></li>
          <li><Link className="signup-btn" to="/signup">Sign Up</Link></li>
        </ul>
      </nav>
    </header>
  );
}
