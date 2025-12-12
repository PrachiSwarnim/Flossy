import { SignUp } from "@clerk/clerk-react";
import "../styles/signup.css";
import Header from "../components/RoleHeader";
import Footer from "../components/Footer";
import { useEffect } from "react";

export default function Signup() {
  useEffect(() => {
    document.title = "Sign Up - Smile Artists Dental Studio";
  }, []);
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", background: "var(--bg-dark)" }}>
      <Header />
      <div className="signup-page" style={{ flex: 1 }}>
        <div className="signup-card">
          <h1>Create Your Account</h1>
          <p>Welcome! Please fill in the details to get started.</p>

          <SignUp
            path="/signup"
            routing="path"
            signInUrl="/login"
            forceRedirectUrl="/post_login"
            signInForceRedirectUrl="/post_login"
            appearance={{
              variables: {
                colorPrimary: "#d4af37",
                colorText: "#ffffff",
                colorBackground: "#1a1a1a",
                colorInputBackground: "#2a2a2a",
                colorInputText: "#ffffff",
                colorTextSecondary: "#cccccc",
              },
              elements: {
                rootBox: {
                  width: "100%",
                  maxWidth: "420px",
                  margin: "0 auto",
                },
                card: {
                  background: "#1f1f1f",
                  backdropFilter: "blur(20px)",
                  borderRadius: "22px",
                  boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
                  padding: "24px",
                  border: "1px solid #333",
                },
                headerTitle: { display: "none" },
                headerSubtitle: { display: "none" },
                socialButtonsBlockButton: {
                  background: "#333",
                  border: "1px solid #555",
                  color: "#fff",
                },
                socialButtonsBlockButtonText: {
                  color: "#fff",
                },
                formButtonPrimary: {
                  background: "linear-gradient(135deg, #d4af37, #f0c455)",
                  color: "#1a1a1a",
                  border: "none",
                  fontWeight: "bold",
                },
                formFieldInput: {
                  border: "1px solid #d4af37", // Gold Border for visibility
                  backgroundColor: "#2a2a2a",
                  color: "#ffffff",
                },
                formFieldLabel: {
                  color: "#ddd",
                },
                footerActionLink: {
                  color: "#d4af37",
                }
              },
            }}
          />

        </div>
      </div>
      <Footer />
    </div>
  );
}
