import { SignUp } from "@clerk/clerk-react";
import "../styles/login.css";
import Footer from "../components/Footer";
import { useEffect } from "react";
import { motion } from "framer-motion";

export default function Signup() {
  useEffect(() => {
    document.title = "Sign Up | Smile Artists";
  }, []);

  return (
    <div className="auth-root">
      {/* ── Left brand panel ── */}
      <motion.div
        className="auth-brand-panel"
        initial={{ opacity: 0, x: -40 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.7 }}
      >
        <div className="auth-orb auth-orb--top" />
        <div className="auth-orb auth-orb--bottom" />

        <div className="auth-brand-content">
          <div className="auth-logo-row" style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer" }} onClick={() => window.location.href = "/"}>
            <img
              src="/static/assets/logo.png"
              alt="Smile Artists"
              style={{ width: "42px", height: "42px", borderRadius: "50%", border: "1px solid rgba(212, 175, 55, 0.4)", objectFit: "cover" }}
            />
            <div style={{ display: "flex", flexDirection: "column", lineHeight: "1.1", alignItems: "flex-end" }}>
              <span style={{ color: "#fff", fontSize: "1.35rem", fontWeight: "bold", fontFamily: "var(--font-heading)" }}>Smile Artists</span>
              <span style={{ color: "#d4af37", fontSize: "0.8rem", fontFamily: "'Monotype Corsiva', cursive", opacity: 0.8 }}>...crafting smiles</span>
            </div>
          </div>
          <h2 className="auth-brand-headline">
            Your Practice,<br />
            <span className="auth-brand-accent">Elevated.</span>
          </h2>
          <p className="auth-brand-sub">
            Join hundreds of dental professionals using FlossyAI to deliver
            exceptional, technology-forward patient care.
          </p>

          <div className="auth-feature-list">
            {[
              { icon: "🔒", label: "Secure Role-Based Access" },
              { icon: "📊", label: "Patient Analytics Dashboard" },
              { icon: "📋", label: "Digital Prescriptions & X-rays" },
              { icon: "🌐", label: "Cloud-Native, Always Available" },
            ].map(({ icon, label }) => (
              <div className="auth-feature-item" key={label}>
                <span className="auth-feature-icon">{icon}</span>
                <span className="auth-feature-label">{label}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="auth-brand-footer">
          © 2025 Smile Artists Dental Studio · Powered by <strong>FlossyAI</strong>
        </p>
      </motion.div>

      {/* ── Right form panel ── */}
      <div className="auth-form-panel">
        <div className="auth-form-glow" />

        <motion.div
          className="auth-form-card"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
        >
          <SignUp
            path="/signup"
            routing="path"
            signInUrl="/login"
            forceRedirectUrl="/post_login"
            signInForceRedirectUrl="/post_login"
            appearance={{
              variables: {
                colorPrimary: "#d4af37",
                colorText: "#f0f0f0",
                colorBackground: "transparent",
                colorInputBackground: "#1e1e1e",
                colorInputText: "#ffffff",
                colorTextSecondary: "#aaaaaa",
                fontFamily: "'Inter', sans-serif",
                borderRadius: "10px",
              },
              elements: {
                rootBox: { width: "100%", margin: "0 auto" },
                card: {
                  background: "transparent",
                  boxShadow: "none",
                  padding: "0",
                  width: "100%",
                  border: "none",
                },
                headerTitle: {
                  fontSize: "1.6rem",
                  fontWeight: "700",
                  color: "#ffffff",
                  fontFamily: "'Playfair Display', serif",
                },
                headerSubtitle: { color: "#999", fontSize: "0.9rem" },
                socialButtonsBlockButton: {
                  background: "#1e1e1e",
                  border: "1px solid #333",
                  color: "#fff",
                  borderRadius: "10px",
                  width: "100%",
                },
                socialButtonsBlockButtonText: { color: "#fff", fontWeight: "500" },
                formButtonPrimary: {
                  background: "linear-gradient(135deg, #c9a227, #f0c455)",
                  color: "#111",
                  border: "none",
                  fontWeight: "700",
                  letterSpacing: "0.02em",
                  borderRadius: "10px",
                },
                formFieldInput: {
                  background: "#1e1e1e",
                  border: "1px solid #333",
                  color: "#fff",
                  borderRadius: "10px",
                },
                formFieldLabel: { color: "#bbb", fontSize: "0.85rem" },
                dividerLine: { background: "#333" },
                dividerText: { color: "#666" },
                footerActionLink: { color: "#d4af37", fontWeight: "600" },
              },
            }}
          />
        </motion.div>
      </div>
    </div>
  );
}
