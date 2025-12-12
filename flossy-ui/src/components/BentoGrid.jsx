import React from "react";
import { motion } from "framer-motion";
import "../styles/bento_grid.css";

const features = [
    {
        id: 1,
        title: "AI-Powered Diagnostics",
        desc: "Instant analysis of dental scans with high accuracy.",
        icon: "fas fa-brain",
        size: "large", // spans 2 columns
        color: "#e0f7fa",
    },
    {
        id: 2,
        title: "Expert Team",
        desc: "Top 1% of dental specialists.",
        icon: "fas fa-user-md",
        size: "medium",
        color: "#fff8e1",
    },
    {
        id: 3,
        title: "24/7 Care",
        desc: "Emergency support always available.",
        icon: "fas fa-clock",
        size: "small",
        color: "#f3e5f5",
    },
    {
        id: 4,
        title: "Modern Tech",
        desc: "State-of-the-art equipment.",
        icon: "fas fa-microscope",
        size: "small",
        color: "#e8f5e9",
    },
    {
        id: 5,
        title: "Painless Treatment",
        desc: "Advanced anesthesia protocols.",
        icon: "fas fa-smile",
        size: "medium", // spans 2 columns
        color: "#fff3e0",
    },
];

export default function BentoGrid() {
    return (
        <section id="ai" className="bento-section" style={{ background: "var(--bg-dark)", padding: "4rem 5%" }}>
            <div className="bento-header" style={{ textAlign: "center", marginBottom: "3rem" }}>
                <motion.h2
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    style={{ fontSize: "3rem", color: "var(--text-light)", fontFamily: "var(--font-heading)" }}
                >
                    Powered by <span style={{ color: "var(--primary-gold)" }}>FlossyAI</span>
                </motion.h2>
                <motion.p
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    transition={{ delay: 0.2, duration: 0.6 }}
                    style={{ color: "var(--text-muted)", fontSize: "1.2rem", maxWidth: "700px", margin: "0 auto" }}
                >
                    Our advanced AI assistant ensures 24/7 care, instant diagnostics, and seamless booking.
                </motion.p>
            </div>

            <div className="bento-grid" style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "1.5rem",
                flexWrap: "nowrap", /* Force single line */
                overflowX: "auto" /* Safety scroll on very small screens */
            }}>
                {[
                    { title: "24/7 Availability", desc: "Always here to answer.", icon: "fas fa-clock" },
                    { title: "Smart Booking", desc: "Effortless appointments.", icon: "fas fa-calendar-check" },
                    { title: "Instant Answers", desc: "Immediate info.", icon: "fas fa-bolt" },
                    { title: "Symptom Analysis", desc: "AI-driven triage.", icon: "fas fa-heartbeat" }
                ].map((feature, i) => (
                    <motion.div
                        key={i}
                        className="bento-card"
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1, duration: 0.5 }}
                        style={{
                            background: "var(--bg-card)",
                            padding: "1.5rem", /* Reduced padding */
                            borderRadius: "4px",
                            border: "1px solid rgba(255,255,255,0.05)",
                            boxShadow: "0 10px 30px rgba(0,0,0,0.3)",
                            flex: "1", /* Distribute space evenly */
                            minWidth: "200px" /* Prevent crushing */
                        }}
                    >
                        <div style={{ fontSize: "1.5rem", color: "var(--primary-gold)", marginBottom: "0.8rem" }}>
                            <i className={feature.icon}></i>
                        </div>
                        <h3 style={{ color: "var(--text-light)", fontFamily: "var(--font-heading)", marginBottom: "0.2rem", fontSize: "1rem" }}>{feature.title}</h3>
                        <p style={{ color: "var(--text-muted)", fontWeight: "300", fontSize: "0.85rem", margin: 0 }}>{feature.desc}</p>
                    </motion.div>
                ))}
            </div>
        </section>
    );
}
