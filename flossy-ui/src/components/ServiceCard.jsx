import { motion } from "framer-motion";
import "../styles/service_card.css";

export default function ServiceCard({ img, title, desc }) {
  return (
    <motion.div
      className="service-card"
      whileHover={{ y: -10, scale: 1.02 }}
      transition={{ type: "spring", stiffness: 300 }}
      style={{ position: "relative", overflow: "hidden" }}
    >
      <div
        className="card-glow"
        style={{
          position: "absolute",
          inset: 0,
          background: "radial-gradient(circle at center, rgba(212, 175, 55, 0.15) 0%, transparent 70%)",
          opacity: 0,
          transition: "opacity 0.3s ease"
        }}
      />
      <style>{`
        .service-card:hover .card-glow { opacity: 1 !important; }
      `}</style>

      <img src={img} alt={title} style={{ zIndex: 1, position: "relative" }} />
      <div className="content" style={{ zIndex: 1, position: "relative" }}>
        <h3>{title}</h3>
        <p>{desc}</p>
      </div>
    </motion.div>
  );
}
