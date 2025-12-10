import "../styles/contact_info.css";

export default function ContactInfo() {
  return (
    <section className="contact-info">
      <h2>Clinic Information</h2>

      <div className="info-grid">
        <div>
          <h3>📍 Address</h3>
          <p>Smile Artists Dental Studio<br />Bangalore, India</p>
        </div>

        <div>
          <h3>📞 Phone</h3>
          <p>+91 98765 43210</p>
        </div>

        <div>
          <h3>⏰ Working Hours</h3>
          <p>Mon–Sat: 9am – 8pm</p>
        </div>
      </div>

      <iframe
        title="Smile Artists Location"
        src="https://www.google.com/maps/embed?pb=!1m18..."
        allowFullScreen
        loading="lazy"
      ></iframe>
    </section>
  );
}
