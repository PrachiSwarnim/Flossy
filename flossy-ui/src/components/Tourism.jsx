import React from "react";
import TourismHero from "./TourismHero";
import TourismContent from "./TourismContent";
import TourismProcess from "./TourismProcess";
import TourismGallery from "./TourismGallery";

export default function Tourism() {
    return (
        <section id="tourism">
            <TourismHero />
            <TourismContent />
            <TourismProcess />
            {/* Divider as requested */}
            <div className="golden-divider"></div>
            <TourismGallery />
        </section>
    );
}
