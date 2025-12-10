import ServiceCard from "./ServiceCard";
import "../styles/services_grid.css";

export default function ServicesGrid({ services }) {
  return (
    <section className="services-grid">
      {services.map((s) => (
        <ServiceCard key={s.title} {...s} />
      ))}
    </section>
  );
}
