import "../styles/hero.css";

export default function Hero() {
  return (
    <section className="hero">
      <div className="hero-text">
        <h1>Crafting <span>Smarter Smiles</span></h1>
        <p>
          Welcome to <strong>Smile Artist Dental Studio</strong> — where artistry meets innovation.
          Experience advanced dental care enhanced by <strong>FlossyAI</strong>.
        </p>
        <button className="btn">Get Started</button>
      </div>

      <div className="hero-image">
        <img src="/static/assets/tooth11.jpg" alt="Smile Hero" />
      </div>
    </section>
  );
}
