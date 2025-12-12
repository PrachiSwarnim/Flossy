import "../styles/contact_modern.css";

export default function ContactSection() {
  return (
    <section className="contact-modern">
      <h1 className="contact-title">Contact Us</h1>

      <div className="contact-cards">
        {/* Call Us */}
        <div className="contact-card-modern">
          <div className="icon-box">
            <i className="fas fa-phone-alt"></i>
          </div>
          <div className="card-content">
            <h2>Call Us</h2>
            <p>+91-8507-213-999</p>
            <p>+91-9693-288-488</p>
          </div>
        </div>

        {/* Email Us */}
        <div className="contact-card-modern">
          <div className="icon-box">
            <i className="fas fa-envelope"></i>
          </div>
          <div className="card-content">
            <h2>Email Us</h2>
            <p>info@smileartists.in</p>
            <p>www.smileartists.in</p>
          </div>
        </div>

        {/* Visit Us */}
        <div className="contact-card-modern">
          <div className="icon-box">
            <i className="fas fa-map-marker-alt"></i>
          </div>
          <div className="card-content">
            <h2>Visit Us</h2>
            <p>573, Smile Artists Dental Studio</p>
            <p>Artemis Hospital Road, Koyal Vihar</p>
            <p>Gurugram – 122003, Haryana, India</p>
            <p className="time"><i className="far fa-clock"></i> 11:00 AM – 8:00 PM (Mon–Sun)</p>
            <a href="#" className="map-link">View on Google Maps &rarr;</a>
          </div>
        </div>
      </div>
    </section>
  );
}
