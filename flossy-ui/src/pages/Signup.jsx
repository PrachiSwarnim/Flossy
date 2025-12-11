import { SignUp } from "@clerk/clerk-react";
import "../styles/signup.css";
import RoleHeader from "../components/RoleHeader";
import Footer from "../components/Footer";
import { useEffect } from "react";

export default function Signup() {
  useEffect(() => {
    document.title = "Sign Up - Smile Artists Dental Studio";
  }, []);
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <RoleHeader />
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
              elements: {
                rootBox: {
                  width: "100%",
                  maxWidth: "420px",
                  margin: "0 auto",
                },
                card: {
                  background: "rgba(255,255,255,0.9)",
                  backdropFilter: "blur(20px)",
                  borderRadius: "22px",
                  boxShadow: "0 10px 40px rgba(252,163,17,0.25)",
                  padding: "24px",
                },
                headerTitle: { display: "none" },
                headerSubtitle: { display: "none" },
              },
            }}
          />

        </div>
      </div>
      <Footer />
    </div>
  );
}
