import { useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";

import Header from "../components/Header";
import Footer from "../components/Footer";
import Carousel from "../components/Carousel";
import AboutCarousel from "../components/AboutCarousel";
import ServicesGrid from "../components/ServicesGrid";
import ContactSection from "../components/ContactSection";
import BentoGrid from "../components/BentoGrid";
import Team from "../components/Team";
import Tourism from "../components/Tourism";
import { Meteors } from "../components/ui/Meteors";

import { services } from "../data/services";

/* ─── Divider ─── */
const Divider = () => (
  <div className="w-full max-w-5xl mx-auto px-8">
    <div className="h-px bg-gradient-to-r from-transparent via-[#d4af37]/15 to-transparent" />
  </div>
);

/* ─── Section Label pill ─── */
const SectionLabel = ({ children }) => (
  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[0.68rem] font-semibold uppercase tracking-widest text-[#d4af37] bg-[#d4af37]/10 border border-[#d4af37]/20 mb-4">
    {children}
  </span>
);

/* ─── HOW IT WORKS data ─── */
const HOW_STEPS = [
  {
    step: "01",
    icon: "fas fa-user-plus",
    title: "Create Your Account",
    desc: "Sign up in under a minute with just your email. No forms, no hassle.",
  },
  {
    step: "02",
    icon: "fas fa-calendar-alt",
    title: "Book Your Appointment",
    desc: "Browse available slots and confirm with one click. FlossyAI suggests the best time for you.",
  },
  {
    step: "03",
    icon: "fas fa-tooth",
    title: "Visit & Smile",
    desc: "Walk in, receive world-class dental care, and walk out with a brighter, healthier smile.",
  },
];

/* ─── STATS data ─── */
const STATS = [
  { value: "10,000+", label: "Happy Patients" },
  { value: "8", label: "Years of Excellence" },
  { value: "Top 1%", label: "Specialist Dentists" },
  { value: "4.9 / 5", label: "Patient Rating" },
];

export default function Home() {
  useEffect(() => {
    document.title = "Smile Artists Dental Studio | Best Dental Clinic in Gurugram";
  }, []);

  return (
    <div className="bg-[#0f0f0f] min-h-screen text-white" style={{ fontFamily: "Inter, sans-serif" }}>
      <Header />

      {/* ══════════════════════════════════════
          HERO — full carousel with headline overlay
      ══════════════════════════════════════ */}
      <section className="relative overflow-hidden" style={{ padding: 0 }}>
        <Carousel />
      </section>

      {/* ══════════════════════════════════════
          SOCIAL PROOF BAR
      ══════════════════════════════════════ */}
      <div className="bg-[#111111] border-y border-white/[0.06] py-6 px-6 overflow-x-auto">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="flex items-center justify-center gap-8 md:gap-16 min-w-max mx-auto"
        >
          {STATS.map((s, i) => (
            <div key={i} className="text-center flex-shrink-0">
              <div
                className="text-[1.6rem] font-bold text-[#d4af37]"
                style={{ fontFamily: "'Playfair Display', serif" }}
              >
                {s.value}
              </div>
              <div className="text-white/40 text-[0.72rem] uppercase tracking-widest mt-0.5">{s.label}</div>
            </div>
          ))}
        </motion.div>
      </div>

      {/* ══════════════════════════════════════
          APPOINTMENT CTA — 2 col hero card
      ══════════════════════════════════════ */}
      <section
        id="appointment"
        style={{ scrollMarginTop: "100px" }}
        className="bg-[#0f0f0f] py-24 px-6"
      >
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
            viewport={{ once: true }}
            className="relative rounded-2xl overflow-hidden border border-[#d4af37]/10"
            style={{
              background: "linear-gradient(135deg, #1a1a1a 0%, #141414 60%, #0f0f0f 100%)",
              boxShadow: "0 0 80px rgba(212,175,55,0.04), 0 20px 60px rgba(0,0,0,0.5)",
            }}
          >
            <Meteors number={18} />
            {/* Radial glow */}
            <div
              className="absolute top-0 right-0 w-[500px] h-[500px] pointer-events-none"
              style={{
                background: "radial-gradient(circle at 80% 20%, rgba(212,175,55,0.06) 0%, transparent 60%)",
              }}
            />

            <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-12 p-10 md:p-16 items-center">
              {/* Left — headline */}
              <div>
                <SectionLabel>Book an Appointment</SectionLabel>
                <h2
                  className="text-[2.4rem] md:text-[3rem] text-white leading-tight mb-4"
                  style={{ fontFamily: "'Playfair Display', serif" }}
                >
                  Your Perfect{" "}
                  <span className="text-[#d4af37] italic">Smile</span>{" "}
                  Starts Here
                </h2>
                <p className="text-white/50 text-[0.95rem] leading-relaxed mb-8">
                  Join thousands of happy patients. Book in under 60 seconds — no calls, no wait.
                  FlossyAI finds the best slot for you.
                </p>
                <div className="flex flex-col sm:flex-row gap-4">
                  <Link
                    to="/signup"
                    className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-[#d4af37] text-[#0f0f0f] font-bold text-[0.9rem] uppercase tracking-wider rounded-sm hover:brightness-110 hover:-translate-y-0.5 transition-all duration-200 no-underline shadow-[0_8px_25px_rgba(212,175,55,0.25)]"
                  >
                    Book Now <i className="fas fa-arrow-right text-xs" />
                  </Link>
                  <Link
                    to="/login"
                    className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-transparent border border-white/20 text-white/70 font-semibold text-[0.9rem] uppercase tracking-wider rounded-sm hover:border-[#d4af37]/40 hover:text-white transition-all duration-200 no-underline"
                  >
                    Sign In
                  </Link>
                </div>
              </div>

              {/* Right — feature pills grid */}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { icon: "fas fa-calendar-check", title: "Instant Booking", desc: "Confirm in under 60 seconds" },
                  { icon: "fas fa-user-md", title: "Top Specialists", desc: "Top 1% dentists in India" },
                  { icon: "fas fa-brain", title: "FlossyAI", desc: "AI-guided appointment flow" },
                  { icon: "fas fa-shield-alt", title: "Safe & Hygienic", desc: "ISO-certified protocols" },
                ].map((f, i) => (
                  <div
                    key={i}
                    className="bg-white/[0.03] border border-white/[0.07] rounded-xl p-4 hover:border-[#d4af37]/20 transition-all duration-300"
                  >
                    <i className={`${f.icon} text-[#d4af37] text-lg mb-2 block`} />
                    <div className="text-white text-[0.85rem] font-semibold mb-0.5">{f.title}</div>
                    <div className="text-white/40 text-[0.75rem]">{f.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <Divider />

      {/* ══════════════════════════════════════
          ABOUT — 2 col
      ══════════════════════════════════════ */}
      <section
        id="about"
        style={{ scrollMarginTop: "100px" }}
        className="bg-[#111111] py-24 px-6"
      >
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-16 items-center">
          {/* Text */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7 }}
            viewport={{ once: true }}
          >
            <SectionLabel>About Us</SectionLabel>
            <h2
              className="text-[2.2rem] md:text-[2.8rem] text-white mb-5 leading-tight"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              About{" "}
              <span className="text-[#d4af37] italic">Smile Artists</span>
            </h2>
            <p className="text-white/55 text-[0.95rem] leading-relaxed mb-4">
              We are dedicated to providing the finest dental care in a comfortable, modern environment.
              Our clinic blends art with science to craft smiles that last a lifetime.
            </p>
            <p className="text-white/40 text-[0.88rem] leading-relaxed mb-4">
              From routine checkups to complex full-mouth rehabilitations, our team of experienced specialists
              uses cutting-edge technology to deliver treatments tailored precisely to you.
            </p>
            <p className="text-white/40 text-[0.88rem] leading-relaxed">
              We believe in a patient-first philosophy — keeping you informed, comfortable, and confident
              throughout every step of your dental journey.
            </p>
          </motion.div>

          {/* Carousel */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7 }}
            viewport={{ once: true }}
            className="w-full h-[380px] rounded-2xl overflow-hidden shadow-[0_20px_60px_rgba(0,0,0,0.5)] border border-white/[0.06]"
          >
            <AboutCarousel />
          </motion.div>
        </div>
      </section>

      <Divider />

      {/* ══════════════════════════════════════
          BENEFITS / BENTO GRID
      ══════════════════════════════════════ */}
      <section id="ai" style={{ scrollMarginTop: "100px" }} className="bg-[#0f0f0f]">
        <BentoGrid />
      </section>

      <Divider />

      {/* ══════════════════════════════════════
          HOW IT WORKS — 3 steps
      ══════════════════════════════════════ */}
      <section className="bg-[#111111] py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <SectionLabel>How It Works</SectionLabel>
            <h2
              className="text-[2.2rem] md:text-[2.8rem] text-white leading-tight"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              Get Started in{" "}
              <span className="text-[#d4af37] italic">3 Simple Steps</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {HOW_STEPS.map((s, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.15, duration: 0.6 }}
                viewport={{ once: true }}
                className="relative bg-[#1a1a1a] rounded-xl p-8 border border-white/[0.06] hover:border-[#d4af37]/20 transition-all duration-300 overflow-hidden group"
              >
                {/* Step watermark */}
                <div
                  className="absolute top-4 right-5 text-[4rem] font-black text-white/[0.04] leading-none select-none group-hover:text-[#d4af37]/[0.06] transition-colors duration-300"
                  style={{ fontFamily: "'Playfair Display', serif" }}
                >
                  {s.step}
                </div>

                <div className="w-12 h-12 rounded-lg bg-[#d4af37]/10 border border-[#d4af37]/20 flex items-center justify-center mb-5">
                  <i className={`${s.icon} text-[#d4af37] text-lg`} />
                </div>
                <h3
                  className="text-white text-[1.1rem] mb-2"
                  style={{ fontFamily: "'Playfair Display', serif" }}
                >
                  {s.title}
                </h3>
                <p className="text-white/40 text-[0.85rem] leading-relaxed m-0">{s.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <Divider />

      {/* ══════════════════════════════════════
          TEAM
      ══════════════════════════════════════ */}
      <section id="team" style={{ scrollMarginTop: "100px" }} className="bg-[#0f0f0f]">
        <Team />
      </section>

      <Divider />

      {/* ══════════════════════════════════════
          SERVICES
      ══════════════════════════════════════ */}
      <section id="services" style={{ scrollMarginTop: "100px" }} className="bg-[#111111] py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <SectionLabel>What We Offer</SectionLabel>
            <h2
              className="text-[2.2rem] md:text-[2.8rem] text-white leading-tight"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              Our{" "}
              <span className="text-[#d4af37] italic">Services</span>
            </h2>
          </div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <ServicesGrid services={services} />
          </motion.div>
        </div>
      </section>

      <Divider />

      {/* ══════════════════════════════════════
          DENTAL TOURISM
      ══════════════════════════════════════ */}
      <section id="tourism" style={{ scrollMarginTop: "100px" }} className="bg-[#0f0f0f]">
        <Tourism />
      </section>

      <Divider />

      {/* ══════════════════════════════════════
          FINAL CTA BANNER
      ══════════════════════════════════════ */}
      <section className="bg-[#111111] py-24 px-6">
        <div className="max-w-3xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
            viewport={{ once: true }}
            className="relative text-center rounded-2xl overflow-hidden border border-[#d4af37]/15 p-12"
            style={{
              background: "linear-gradient(135deg, #1c1a10 0%, #141410 50%, #111111 100%)",
              boxShadow: "0 0 60px rgba(212,175,55,0.05), 0 20px 60px rgba(0,0,0,0.4)",
            }}
          >
            <Meteors number={12} />
            {/* Glow */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: "radial-gradient(ellipse at 50% 0%, rgba(212,175,55,0.08) 0%, transparent 65%)",
              }}
            />
            <div className="relative z-10">
              <SectionLabel>Limited Slots Available</SectionLabel>
              <h2
                className="text-[2.2rem] md:text-[3rem] text-white mb-4 leading-tight"
                style={{ fontFamily: "'Playfair Display', serif" }}
              >
                Ready to Transform{" "}
                <span className="text-[#d4af37] italic">Your Smile?</span>
              </h2>
              <p className="text-white/50 text-[0.95rem] mb-8 max-w-xl mx-auto leading-relaxed">
                Join over 10,000 happy patients who trust Smile Artists for world-class dental care.
                Book your appointment today — it takes less than 60 seconds.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  to="/signup"
                  className="inline-flex items-center justify-center gap-2 px-10 py-4 bg-[#d4af37] text-[#0f0f0f] font-bold text-[0.9rem] uppercase tracking-wider rounded-sm hover:brightness-110 hover:-translate-y-0.5 transition-all duration-200 no-underline shadow-[0_8px_30px_rgba(212,175,55,0.3)]"
                >
                  Book Free Consultation <i className="fas fa-arrow-right text-xs" />
                </Link>
                <a
                  href="#contact"
                  className="inline-flex items-center justify-center gap-2 px-10 py-4 bg-transparent border border-white/20 text-white/70 font-semibold text-[0.9rem] uppercase tracking-wider rounded-sm hover:border-[#d4af37]/40 hover:text-white transition-all duration-200 no-underline"
                >
                  Contact Us
                </a>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <Divider />

      {/* ══════════════════════════════════════
          CONTACT
      ══════════════════════════════════════ */}
      <section id="contact" style={{ scrollMarginTop: "100px" }} className="bg-[#0f0f0f]">
        <ContactSection />
      </section>

      <Footer />
    </div>
  );
}
