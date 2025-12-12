import { useEffect } from "react";

import Header from "../components/Header";
import Footer from "../components/Footer";

import Carousel from "../components/Carousel";
import Hero from "../components/Hero";
import About from "../components/About";
import Team from "../components/Team";
import AISection from "../components/AISection";
import InstagramSection from "../components/InstagramSection";

import AppointmentRequestForm from "../components/AppointmentRequestForm";
import ContactSection from "../components/ContactSection";

// SPA Imports
import ServicesHero from "../components/ServicesHero";
import ServicesGrid from "../components/ServicesGrid";
import TourismHero from "../components/TourismHero";
import TourismContent from "../components/TourismContent";
import TourismGallery from "../components/TourismGallery";

import { services } from "../data/services";

export default function Home() {
    useEffect(() => {
        document.title = "Smile Artists";
    }, []);

    return (
        <>
            <Header />

            <Carousel />
            <Hero />

            <div id="about" className="homepage-section" style={{ scrollMarginTop: "100px" }}>
                <About />
            </div>

            <div id="services" className="homepage-section" style={{ scrollMarginTop: "100px" }}>
                <ServicesHero />
                <ServicesGrid services={services} />
            </div>

            <div id="tourism" className="homepage-section" style={{ scrollMarginTop: "100px" }}>
                <TourismHero />
                <TourismContent />
                <TourismGallery />
            </div>

            <div id="team" className="homepage-section" style={{ scrollMarginTop: "100px" }}>
                <Team />
            </div>

            <div id="ai" className="homepage-section" style={{ scrollMarginTop: "100px" }}>
                <AISection />
            </div>

            {/* APPOINTMENT FORM */}
            <div id="appointment" className="homepage-section" style={{ scrollMarginTop: "100px" }}>
                <AppointmentRequestForm />
            </div>

            <div id="contact" className="homepage-section" style={{ scrollMarginTop: "100px" }}>
                <ContactSection />
            </div>

            <InstagramSection />

            <Footer />
        </>
    );
}
