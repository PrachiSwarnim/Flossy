import { useRef } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import Header from "../components/Header";
import Footer from "../components/Footer";
import Carousel from "../components/Carousel";
import ServicesGrid from "../components/ServicesGrid";
import AppointmentRequestForm from "../components/AppointmentRequestForm";
import ContactSection from "../components/ContactSection";
import BentoGrid from "../components/BentoGrid";
import Team from "../components/Team";
import { useEffect } from "react";

import { services } from "../data/services";
import Tourism from "../components/Tourism";

import "../styles/global.css";
import "../styles/hero.css";
import "../styles/hero.css";
import "../styles/about.css";
import VoiceChat from "../components/VoiceChat";
import { useState } from "react";

export default function Home() {
    useEffect(() => {
        document.title = "Smile Artists Dental Studio | Best Dental Clinic in Gurugram";
    }, []);
    const servicesRef = useRef(null);
    const [isCallOpen, setIsCallOpen] = useState(false);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
        >
            <Header servicesRef={servicesRef} />

            {/* HERO SECTION */}
            <section className="homepage-section" style={{ padding: 0 }}>
                <Carousel />

                {/* Floating Appointment Form */}
                <motion.div
                    id="appointment"
                    className="hero-form-container"
                    style={{ scrollMarginTop: "120px" }}
                    initial={{ y: 50, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.5, duration: 0.8 }}
                >
                    <AppointmentRequestForm />
                </motion.div>
            </section>



            {/* DIVIDER */}
            <div className="section-divider"></div>

            {/* ABOUT SECTION */}
            <section id="about" className="homepage-section" style={{ scrollMarginTop: "100px" }}>
                <div className="about-container">
                    <motion.div
                        className="about-text"
                        initial={{ x: -50, opacity: 0 }}
                        whileInView={{ x: 0, opacity: 1 }}
                        transition={{ duration: 0.6 }}
                        viewport={{ once: true }}
                    >
                        <h2>About <span style={{ color: "var(--primary-gold)" }}>Smile Artists</span></h2>
                        <p className="lead-text">
                            We are dedicated to providing the best dental care in a comfortable and relaxing environment.
                        </p>
                        <p>
                            Our team of experienced dentists uses the latest technology to ensure you get the best treatment possible.
                            From routine checkups to complex surgeries, we are here to help you achieve the perfect smile.
                        </p>
                        <p>
                            We believe in a patient-first approach, ensuring that you are informed and comfortable throughout your treatment journey.
                        </p>
                    </motion.div>
                    <motion.div
                        className="about-image"
                        initial={{ x: 50, opacity: 0 }}
                        whileInView={{ x: 0, opacity: 1 }}
                        transition={{ duration: 0.6 }}
                        viewport={{ once: true }}
                    >
                        {/* <img src="/assets/images/clinic_interior.jpg" alt="Clinic Interior" /> */}
                        <div className="image-placeholder" style={{
                            width: "100%",
                            height: "300px",
                            background: "#e0e0e0",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            borderRadius: "20px",
                            color: "#888"
                        }}>
                            [Clinic Interior Image Placeholder]
                        </div>
                        <div className="image-decoration"></div>
                    </motion.div>
                </div>
            </section>

            {/* DIVIDER */}
            <div className="section-divider"></div>

            {/* TEAM SECTION (New) */}
            <div id="team" className="homepage-section" style={{ scrollMarginTop: "100px" }}>
                <Team />
            </div>

            {/* DIVIDER */}
            <div className="section-divider"></div>



            {/* FLOSSY AI SHOWCASE (Bento Grid) */}
            <div id="ai" className="homepage-section" style={{ scrollMarginTop: "100px" }}>
                <BentoGrid />
            </div>

            {/* DIVIDER */}
            <div className="section-divider"></div>

            {/* DENTAL TOURISM (Restored) */}
            <div className="homepage-section" style={{ scrollMarginTop: "100px" }}>
                <Tourism />
            </div>

            {/* DIVIDER */}
            <div className="section-divider"></div>

            {/* SERVICES SECTION */}
            <section id="services" ref={servicesRef} className="homepage-section force-dark-bg" style={{ scrollMarginTop: "100px", background: "var(--bg-dark)" }}>
                {/* ... existing services content ... */}
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    viewport={{ once: true }}
                >
                    <h2 style={{
                        textAlign: "center",
                        fontSize: "2.5rem",
                        marginBottom: "1rem",
                        color: "var(--text-light)", /* Fixed color */
                        fontFamily: "var(--font-heading)"
                    }}>
                        Our <span style={{ color: "var(--primary-gold)" }}>Services</span>
                    </h2>
                    <ServicesGrid services={services} />
                </motion.div>
            </section>

            {/* DIVIDER */}
            <div className="section-divider"></div>

            {/* CONTACT SECTION */}
            <div id="contact" className="homepage-section" style={{ scrollMarginTop: "100px" }}>
                <ContactSection />
            </div>

            <Footer />

            {/* VOICE CALL MODAL & TRIGGER */}
            {isCallOpen && (
                <VoiceChat onClose={() => setIsCallOpen(false)} />
            )}
            <button
                style={{
                    position: "fixed",
                    bottom: "20px",
                    left: "20px",
                    zIndex: 999,
                    background: "#f0b800",
                    border: "none",
                    borderRadius: "50px",
                    padding: "15px 25px",
                    fontSize: "16px",
                    fontWeight: "bold",
                    color: "#000",
                    boxShadow: "0 4px 15px rgba(240, 184, 0, 0.4)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "10px"
                }}
                onClick={() => setIsCallOpen(true)}
            >
                <i className="fas fa-phone-volume"></i> Talk to AI
            </button>
        </motion.div>
    );
}
