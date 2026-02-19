import TourismHero from "./TourismHero";
import TourismContent from "./TourismContent";
import TourismProcess from "./TourismProcess";
import TourismGallery from "./TourismGallery";

export default function Tourism() {
  return (
    <div className="bg-[#0f0f0f]">
      <TourismHero />
      <TourismContent />
      <TourismProcess />
      <div className="w-full max-w-5xl mx-auto px-8 my-4">
        <div className="h-px bg-gradient-to-r from-transparent via-[#d4af37]/15 to-transparent" />
      </div>
      <TourismGallery />
    </div>
  );
}
