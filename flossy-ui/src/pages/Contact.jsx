import { useEffect, useState } from "react";
import ContactHeader from "../components/ContactHeader";
import ContactSection from "../components/ContactSection";
import Footer from "../components/Footer";
import { PropagateLoader } from "react-spinners";

export default function Contact() {
  const [pageLoading, setPageLoading] = useState(true);

  useEffect(() => {
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
      <ContactHeader />
      <ContactSection />
      <Footer />
    </>
  );
}
