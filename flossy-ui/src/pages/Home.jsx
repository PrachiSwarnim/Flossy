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
import "../styles/about.css";
import VoiceChat from "../components/VoiceChat";
import { Spotlight } from "../components/ui/Spotlight";
import { Meteors } from "../components/ui/Meteors";
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
            <section className="homepage-section" style={{ padding: 0, overflow: "hidden" }}>
                <Carousel />

                {/* Floating Appointment Form - Centered via Wrapper */}
                <div className="hero-form-container">
                    <Spotlight
                        className=""
                        fill="white"
                        style={{ top: "-50%", left: "-20%", opacity: 0.5, transform: "rotate(-45deg)" }}
                    />
                    <motion.div
                        id="appointment"
                        style={{ scrollMarginTop: "120px" }}
                        initial={{ y: 50, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        transition={{ delay: 0.5, duration: 0.8 }}
                    >
                        {/* <AppointmentRequestForm /> */}
                        <motion.div
                            whileHover={{ scale: 1.05, boxShadow: "0 0 40px rgba(212, 175, 55, 0.6), 0 30px 60px rgba(0,0,0,0.6)" }}
                            transition={{ type: "spring", stiffness: 300, damping: 20 }}
                            style={{
                                background: "url('/static/assets/image.jpg') center/cover no-repeat",
                                position: "relative",
                                padding: "2.5rem",
                                borderRadius: "20px",
                                border: "1px solid rgba(255, 255, 255, 0.2)",
                                maxWidth: "400px",
                                width: "100%",
                                boxShadow: "0 0 25px rgba(212, 175, 55, 0.4), 0 25px 50px rgba(0,0,0,0.5)",
                                textAlign: "center",
                                overflow: "hidden"
                            }}>
                            <Meteors number={20} />
                            {/* Dark Overlay for readability */}
                            <div style={{
                                position: "absolute",
                                top: 0,
                                left: 0,
                                right: 0,
                                bottom: 0,
                                background: "rgba(0, 0, 0, 0.4)",
                                backdropFilter: "blur(3px)",
                                zIndex: 1
                            }}></div>

                            {/* Content */}
                            <div style={{ position: "relative", zIndex: 2 }}>
                                <h3 style={{
                                    color: "var(--primary-gold)",
                                    fontSize: "2rem",
                                    marginBottom: "1rem",
                                    fontFamily: "var(--font-heading)",
                                    textShadow: "0 2px 4px rgba(0,0,0,0.8)"
                                }}>Book Your Visit</h3>

                                <p style={{
                                    color: "#ccc",
                                    marginBottom: "2rem",
                                    lineHeight: "1.6",
                                    fontSize: "1.05rem"
                                }}>
                                    To provide you with personalized care, please create a patient account to schedule your appointment instantly.
                                </p>

                                <Link to="/signup" style={{
                                    display: "block",
                                    width: "100%",
                                    padding: "16px",
                                    background: "linear-gradient(135deg, #f0b800 0%, #d4a000 100%)",
                                    color: "#000",
                                    fontWeight: "bold",
                                    fontSize: "1.1rem",
                                    borderRadius: "12px",
                                    textDecoration: "none",
                                    marginBottom: "1rem",
                                    transition: "transform 0.2s"
                                }}>
                                    Create Patient Account
                                </Link>

                                <div style={{ color: "#aaa", fontSize: "0.9rem", textShadow: "0 1px 2px rgba(0,0,0,0.8)" }}>
                                    Already have an account? <Link to="/login" style={{ color: "var(--primary-gold)", textDecoration: "none", fontWeight: "bold" }}>Log In</Link>
                                </div>
                            </div>
                        </motion.div>
                    </motion.div>
                </div>
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
