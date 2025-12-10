import "../styles/service_card.css";

export default function ServiceCard({ img, title, desc }) {
  return (
    <div className="service-card">
      <img src={img} alt={title} />
      <div className="content">
        <h3>{title}</h3>
        <p>{desc}</p>
      </div>
    </div>
  );
}
