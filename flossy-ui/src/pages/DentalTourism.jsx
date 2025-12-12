import { useEffect } from "react";
import Header from "../components/Header";
import TourismHero from "../components/TourismHero";
import TourismContent from "../components/TourismContent";
import TourismGallery from "../components/TourismGallery";
import Footer from "../components/Footer";
import "../styles/tourism_page.css"; // 🔥 Add this
import "../styles/global.css";
export default function DentalTourism() {
  useEffect(() => {
    document.title = "Dental Tourism | Smile Artists";
  }, []);

  return (

    <div className="tourism-page" style={{ background: "var(--bg-dark)", minHeight: "100vh" }}>
      <Header />
      <TourismHero />
      <TourismContent />
      <TourismGallery />
      <Footer />
    </div>
  );
}
