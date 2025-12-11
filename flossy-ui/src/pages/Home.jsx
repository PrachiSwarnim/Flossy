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

            <div id="about">
                <About />
            </div>

            <div id="services">
                <ServicesHero />
                <ServicesGrid services={services} />
            </div>

            <div id="tourism">
                <TourismHero />
                <TourismContent />
                <TourismGallery />
            </div>

            <div id="team">
                <Team />
            </div>

            <AISection />

            {/* APPOINTMENT FORM */}
            <div id="appointment">
                <AppointmentRequestForm />
            </div>

            <InstagramSection />

            <Footer />
        </>
    );
}
