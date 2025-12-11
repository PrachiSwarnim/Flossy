import "../styles/header.css";

export default function Header() {
  return (
    <header className="header">
      <div className="logo">
        <img src="/static/assets/logo.png" alt="Smile Artists Logo" />
        <span>Smile Artists</span>
      </div>

      <nav>
        <ul>
          <li><a href="/#about">About</a></li>
          <li><a href="/#ai">FlossyAI</a></li>
          <li><a href="/services">Our Services</a></li>
          <li><a href="/tourism">Dental Tourism</a></li>
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
