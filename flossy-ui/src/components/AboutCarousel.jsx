import { useState, useEffect, useRef } from "react";
import "../styles/about-carousel.css";

export default function AboutCarousel() {
    const images = [
        "/static/assets/Clinic Interior 4.jpg",
        "/static/assets/Clinic Interior 2.jpg",
        "/static/assets/Clinic Interior 3.jpg",
        "/static/assets/Clinic Interior 1.jpg",
        "/static/assets/Clinic Interior 5.jpg",
    ];

    const [index, setIndex] = useState(0);
    const transitionRef = useRef(true);

    // Duplicate first slide for smooth loop
    const slides = [...images, images[0]];

    // Move to next slide
    const nextSlide = () => {
        if (index === slides.length - 1) return;
        setIndex((prev) => prev + 1);
    };

    // Move to prev slide
    const prevSlide = () => {
        if (index === 0) {
            return;
        }
        setIndex((prev) => prev - 1);
    };

    // Auto-slide
    useEffect(() => {
        const timer = setInterval(() => {
            setIndex((prev) => prev + 1);
        }, 4000);
        return () => clearInterval(timer);
    }, [index]);

    // Handle Loop Reset
    useEffect(() => {
        if (index === slides.length - 1) {
            setTimeout(() => {
                transitionRef.current = false;
                setIndex(0);
            }, 700);
        }
        else if (index === 0 && transitionRef.current === false) {
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    transitionRef.current = true;
                });
            });
        } else {
            transitionRef.current = true;
        }
    }, [index, slides.length]);

    return (
        <div className="about-carousel">
            {/* LEFT ARROW */}
            <button className="about-carousel-arrow left" onClick={() => setIndex((i) => i === 0 ? images.length - 1 : i - 1)}>
                <i className="fas fa-chevron-left"></i>
            </button>

            {/* RIGHT ARROW */}
            <button className="about-carousel-arrow right" onClick={() => setIndex((i) => i + 1)}>
                <i className="fas fa-chevron-right"></i>
            </button>

            <div className="about-carousel-inner">
                <div
                    className="about-slides"
                    style={{
                        transform: `translateX(-${index * 100}%)`,
                        transition: transitionRef.current ? "transform 0.7s ease-in-out" : "none",
                    }}
                >
                    {slides.map((src, i) => (
                        <div className="about-slide" key={i}>
                            <div
                                className="about-slide-backdrop"
                                style={{ backgroundImage: `url("${src}")` }}
                            ></div>
                            <img src={src} alt={`clinic-interior-${i}`} />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
