import { useEffect, useState } from "react";
import ContactHeader from "../components/ContactHeader";
import ContactSection from "../components/ContactSection";
import Footer from "../components/Footer";
import { PropagateLoader } from "react-spinners";

export default function Contact() {
  const [pageLoading, setPageLoading] = useState(true);

  useEffect(() => {
    document.title = "Contact Us | Smile Artists Dental Studio";
    // Artificial delay to show loader smoothly
    const timer = setTimeout(() => setPageLoading(false), 900);
    return () => clearTimeout(timer);
  }, []);

  return (
    <>
      {/* Page Loader Overlay */}
      {pageLoading && (
        <div className="loader-box">
          <PropagateLoader color="#f8bf09" size={12} />
          <p>Loading contact page…</p>
        </div>
      )}

      {/* Page Content */}
      {/* Page Content */}
      <div style={{ background: "var(--bg-dark)", minHeight: "100vh" }}>
        <ContactHeader />
        <ContactSection />
        <Footer />
      </div>
    </>
  );
}
