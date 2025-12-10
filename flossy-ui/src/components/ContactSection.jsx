import "../styles/contact_modern.css";

export default function ContactSection() {
  return (
    <section className="contact-modern">
      <h1 className="contact-title">Contact Us</h1>

      <div className="contact-cards">
        {/* Call Us */}
        <div className="contact-card-modern">
          <h2>Call Us</h2>
          <p>📞 +91-8507-213-999</p>
          <p>📞 +91-9693-288-488</p>
        </div>

        {/* Email Us */}
        <div className="contact-card-modern">
          <h2>Email Us</h2>
          <p>📧 info@smileartists.in</p>
          <p>🌐 www.smileartists.in</p>
        </div>

        {/* Visit Us */}
        <div className="contact-card-modern">
          <h2>Visit Us</h2>
          <p>📍 573, Smile Artists Dental Studio</p>
          <p>Artemis Hospital Road, Koyal Vihar</p>
          <p>Gurugram – 122003, Haryana, India</p>
          <p>🕒 11:00 AM – 8:00 PM (Mon–Sun)</p>
          <a href="#" className="map-link">Locate Us on Google Maps</a>
        </div>
      </div>
    </section>
  );
}
