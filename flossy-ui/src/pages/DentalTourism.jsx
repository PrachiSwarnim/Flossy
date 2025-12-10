import { useEffect } from "react";
import TourismHeader from "../components/TourismHeader";
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
    <div className="tourism-page">
      <TourismHeader />
      <TourismHero />
      <TourismContent />
      <TourismGallery />
      <Footer />
    </div>
  );
}
