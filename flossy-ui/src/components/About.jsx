import "../styles/about.css";

export default function About() {
  return (
    <section id="about" className="about-section">
      <h2>About Our Studio</h2>

      <p className="animate-fade-up" style={{ animationDelay: "0.2s" }}>
        At Smile Artists Dental Studio, your smile is at the heart of everything we do. Our team of skilled and compassionate professionals is dedicated to making each visit comfortable, calm, and genuinely reassuring.
      </p>

      <p className="animate-fade-up" style={{ animationDelay: "0.4s" }}>
        As an ISO 9001:2015 Certified Clinic, we maintain the highest standards of hygiene and quality. Whether it’s a simple cleaning or a complete smile makeover, we deliver personalized care rooted in precision, expertise, and trust.
      </p>

      <p className="animate-fade-up" style={{ animationDelay: "0.6s" }}>
        Our team — from hygienists and assistants to technicians and support staff — takes pride in creating a smooth, stress-free experience for every patient. We know dental visits can feel overwhelming, so we focus on clarity, comfort, and care at every step.
      </p>

      <p className="animate-fade-up" style={{ animationDelay: "0.8s", fontStyle: "italic", fontWeight: "bold" }}>
        Thank you for choosing us to be a part of your smile journey. We’re grateful for your trust and look forward to welcoming you with warmth, comfort, and confidence!!
      </p>
    </section>
  );
}