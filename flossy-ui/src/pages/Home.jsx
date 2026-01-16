import { useRef } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import Header from "../components/Header";
import Footer from "../components/Footer";
import Carousel from "../components/Carousel";
import AboutCarousel from "../components/AboutCarousel";
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

import { Meteors } from "../components/ui/Meteors";
import { ThreeDCard } from "../components/ui/ThreeDCard";
import { TextGenerateEffect } from "../components/ui/TextGenerateEffect";
import { useState } from "react";

export default function Home() {
    useEffect(() => {
        document.title = "Smile Artists Dental Studio | Best Dental Clinic in Gurugram";
    }, []);
    const servicesRef = useRef(null);

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

                    <motion.div
                        id="appointment"
                        style={{ scrollMarginTop: "120px", perspective: "1000px" }}
                        initial={{ y: 50, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        transition={{ delay: 0.5, duration: 0.8 }}
                    >
                        <ThreeDCard
                            className="booking-card-3d"
                            containerStyle={{
                                background: "url('/static/assets/image.jpg') center/cover no-repeat",
                                position: "relative",
                                padding: "3rem",
                                borderRadius: "20px",
                                border: "1px solid rgba(255, 255, 255, 0.2)",
                                maxWidth: "500px",
                                width: "100%",
                                boxShadow: "0 20px 50px rgba(0,0,0,0.5), 0 0 30px rgba(212, 175, 55, 0.2)",
                                textAlign: "center",
                                margin: "0 auto"
                            }}
                        >
                            <Meteors number={20} />

                            {/* Dark Overlay for readability */}
                            <div style={{
                                position: "absolute",
                                top: 0,
                                left: 0,
                                right: 0,
                                bottom: 0,
                                background: "rgba(0, 0, 0, 0.6)",
                                backdropFilter: "blur(2px)",
                                zIndex: 1,
                                borderRadius: "20px"
                            }}></div>

                            {/* Content */}
                            <div style={{ position: "relative", zIndex: 2 }}>
                                <h3 style={{
                                    color: "var(--primary-gold)",
                                    fontSize: "2.2rem",
                                    marginBottom: "1.2rem",
                                    fontFamily: "var(--font-heading)",
                                    textShadow: "0 2px 4px rgba(0,0,0,0.8)"
                                }}>Book Your Visit</h3>

                                <p style={{
                                    color: "#ddd",
                                    marginBottom: "2.5rem",
                                    lineHeight: "1.6",
                                    fontSize: "1.1rem"
                                }}>
                                    To provide you with personalized care, please create a patient account to schedule your appointment instantly.
                                </p>

                                <Link to="/signup" style={{
                                    display: "block",
                                    width: "100%",
                                    padding: "18px",
                                    background: "linear-gradient(135deg, #f0b800 0%, #d4a000 100%)",
                                    color: "#000",
                                    fontWeight: "bold",
                                    fontSize: "1.2rem",
                                    borderRadius: "12px",
                                    textDecoration: "none",
                                    marginBottom: "1.5rem",
                                    boxShadow: "0 5px 15px rgba(0,0,0,0.3)"
                                }}>
                                    Create Patient Account
                                </Link>

                                <div style={{ color: "#aaa", fontSize: "0.95rem", textShadow: "0 1px 2px rgba(0,0,0,0.8)" }}>
                                    Already have an account? <Link to="/login" style={{ color: "var(--primary-gold)", textDecoration: "none", fontWeight: "bold" }}>Log In</Link>
                                </div>
                            </div>
                        </ThreeDCard>
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
                        {/* <h2>About <span style={{ color: "var(--primary-gold)" }}>Smile Artists</span></h2> */}
                        <div style={{ fontSize: "2.5rem", fontWeight: "bold", marginBottom: "1rem", color: "#fff" }}>
                            <span style={{ display: "inline-block", marginRight: "10px" }}>About</span>
                            <TextGenerateEffect words="Smile Artists" className="inline-block text-gold text-brand" />
                        </div>
                        <style>{` .text-gold span { color: var(--primary-gold) !important; } `}</style>
                        <div style={{ marginBottom: "1.5rem" }}>
                            <TextGenerateEffect
                                words="We are dedicated to providing the best dental care in a comfortable and relaxing environment."
                                className="lead-text"
                            />
                        </div>
                        <div style={{ marginBottom: "1rem", color: "#ccc" }}>
                            <TextGenerateEffect
                                words="Our team of experienced dentists uses the latest technology to ensure you get the best treatment possible. From routine checkups to complex surgeries, we are here to help you achieve the perfect smile."
                            />
                        </div>
                        <div style={{ marginBottom: "1rem", color: "#ccc" }}>
                            <TextGenerateEffect
                                words="We believe in a patient-first approach, ensuring that you are informed and comfortable throughout your treatment journey."
                            />
                        </div>
                    </motion.div>
                    <motion.div
                        className="about-image"
                        initial={{ x: 50, opacity: 0 }}
                        whileInView={{ x: 0, opacity: 1 }}
                        transition={{ duration: 0.6 }}
                        viewport={{ once: true }}
                    >
                        {/* <img src="/assets/images/clinic_interior.jpg" alt="Clinic Interior" /> */}
                        <div className="about-carousel-container" style={{ width: "100%", height: "400px", borderRadius: "20px", overflow: "hidden", position: "relative" }}>
                            <AboutCarousel />
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
        </motion.div>
    );
}
