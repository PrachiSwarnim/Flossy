import "../styles/tourism_process.css";

export default function TourismProcess() {
  return (
    <section className="tourism-process">
      <h2>Dentistry + Tourism: A Seamless Experience</h2>
      <p>Our team ensures a smooth journey — from consultation to after-care.</p>

      <div className="process-grid">
        <div className="step">
          <h3>1. Online Consultation</h3>
          <p>Share your dental concerns and receive a treatment plan.</p>
        </div>

        <div className="step">
          <h3>2. Travel Assistance</h3>
          <p>We help you plan flights and stay for a comfortable visit.</p>
        </div>

        <div className="step">
          <h3>3. Advanced Treatment</h3>
          <p>Receive world-class care using modern equipment.</p>
        </div>

        <div className="step">
          <h3>4. Post-Treatment Support</h3>
          <p>We provide follow-up care to ensure lasting comfort.</p>
        </div>
      </div>
    </section>
  );
}
