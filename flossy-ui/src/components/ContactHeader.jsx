import "../styles/contact_header.css";

export default function ContactHeader() {
  return (
    <header className="contact-header">
      <div className="logo">
        <img src="/static/assets/logo.png" alt="Smile Artists" />
        <span>Smile Artists</span>
      </div>

      <nav>
        <ul>
          <li><a href="/">Home</a></li>
          <li><a href="/services">Services</a></li>
          <li><a href="/tourism">Dental Tourism</a></li>
          <li><a href="/contact">Contact</a></li>
        </ul>
      </nav>
    </header>
  );
}
