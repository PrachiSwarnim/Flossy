  import "../styles/tourism_header.css";

  export default function TourismHeader() {
    return (
      <header className="tourism-header">
        <div className="logo">
          <img src="/static/assets/logo.png" alt="Smile Artists Logo" />
          <span className="name">Smile Artists</span>
        </div>

        <nav>
          <ul>
            <li><a href="/">Home</a></li>
            <li><a href="/services">Services</a></li>
            <li><a href="/#team">Meet the Team</a></li>
            <li><a href="/contact">Contact</a></li>
          </ul>
        </nav>
      </header>
    );
  }
