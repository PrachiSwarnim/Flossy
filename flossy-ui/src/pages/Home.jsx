import { useEffect } from "react";

import Header from "../components/Header";
import Footer from "../components/Footer";

import Carousel from "../components/Carousel";
import Hero from "../components/Hero";
import About from "../components/About";
import Team from "../components/Team";
import AISection from "../components/AISection";
import InstagramSection from "../components/InstagramSection";

export default function Home() {
    useEffect(() => {
        document.title = "Smile Artists";
      }, []);
    return (
        <>
        <Header />

        <Carousel />
        <Hero />
        <About />
        <div id="team">
            <Team />
        </div>
        <AISection />
        <InstagramSection />

        <Footer />
        </>
    );
}
