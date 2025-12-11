import { useEffect } from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import ServicesHero from "../components/ServicesHero";
import ServicesGrid from "../components/ServicesGrid";
import "../styles/services_page.css";
import ServicesHeader from "../components/ServicesHeader";
import { services } from "../data/services";


export default function Services() {
  useEffect(() => {
    document.title = "Our Services — Smile Artists Dental Studio";
  }, []);



  return (
    <div className="services-page">
      <ServicesHeader />
      <ServicesHero />
      <ServicesGrid services={services} />
      <Footer />
    </div>
  );
}
