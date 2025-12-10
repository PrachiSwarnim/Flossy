import { useEffect } from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import ServicesHero from "../components/ServicesHero";
import ServicesGrid from "../components/ServicesGrid";
import "../styles/services_page.css";
import ServicesHeader from "../components/ServicesHeader";


export default function Services() {
  useEffect(() => {
    document.title = "Our Services — Smile Artists Dental Studio";
  }, []);

  const services = [
    {
      title: "Routine Dental Checkup",
      img: "/static/assets/Routine Dental Checkup.avif",
      desc: "Experience comprehensive dental exams, teeth cleaning, and fluoride treatments to prevent dental problems before they occur. We offer personalized care including implant restoration and periodontal treatments."
    },
    {
      title: "Preventive Care & Cosmetic Dentistry",
      img: "/static/assets/Preventive Care & Cosmetic Dentistry.avif",
      desc: "We provide preventive care to maintain oral health and cosmetic dentistry to enhance your smile — restoring beauty and function through modern, gentle techniques."
    },
    {
      title: "Dental Fillings",
      img: "/static/assets/Dental Fillings.avif",
      desc: "We offer both traditional and laser composite fillings to restore decayed or damaged teeth quickly and painlessly for long-lasting dental health."
    },
    {
      title: "Emergency Care & Oral Surgery",
      img: "/static/assets/Emergency Care & Oral Surgery.avif",
      desc: "Our skilled team is ready to handle emergencies like chipped teeth or mouth trauma with advanced surgical techniques and compassionate care."
    },
    {
      title: "Painless Root Canal Treatments",
      img: "/static/assets/Painless Root Canal Treatments.avif",
      desc: "With modern techniques, our one-day root canal treatments are nearly pain-free. Dental crowns are recommended post-treatment for added strength."
    },
    {
      title: "Hollywood Smile Makeover",
      img: "/static/assets/Hollywood Smile Makeover.avif",
      desc: "Transform your smile with our Hollywood Smile Design — where artistry meets dental science for a radiant, confident smile."
    },
    {
      title: "Immediate Implants",
      img: "/static/assets/Immediate Implants.avif",
      desc: "Restore missing teeth in just 48 hours with our immediate implant procedure for a natural, lasting result."
    },
    {
      title: "Kids Dentistry",
      img: "/static/assets/Kids Dentistry.avif",
      desc: "We make dental visits fun and stress-free for kids, ensuring healthy baby teeth and strong foundations for permanent ones."
    },
    {
      title: "Dental Crowns & Bridges",
      img: "/static/assets/Dental Crowns & Bridges.avif",
      desc: "Our ceramic crowns and dental bridges restore damaged or missing teeth, giving you back confidence and function."
    },
    {
      title: "Teeth Whitening",
      img: "/static/assets/Teeth Whitening.avif",
      desc: "Get a smile several shades brighter in just one hour using safe and advanced whitening techniques."
    },
    {
      title: "Wisdom Tooth Removal",
      img: "/static/assets/Wisdom Tooth Removal.avif",
      desc: "Our gentle and effective removal of wisdom teeth prevents pain, infections, and misalignment — restoring comfort quickly."
    },
    {
      title: "Braces & Aligners",
      img: "/static/assets/Braces & Aligners.avif",
      desc: "Choose from metal, ceramic, or clear aligners to achieve a perfectly aligned, confident smile with expert orthodontic care."
    },
    {
      title: "Dentures",
      img: "/static/assets/Dentures.avif",
      desc: "Replace missing teeth with our durable, comfortable complete or partial dentures designed for natural aesthetics & easy maintenance."
    }
  ];

  return (
    <div className="services-page">
      <ServicesHeader />
      <ServicesHero />
      <ServicesGrid services={services} />
      <Footer />
    </div>
  );
}
