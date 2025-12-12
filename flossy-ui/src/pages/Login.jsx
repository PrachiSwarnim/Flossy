import { SignIn } from "@clerk/clerk-react";
import "../styles/login.css";
import Header from "../components/RoleHeader";
import Footer from "../components/Footer";
import { useEffect } from "react";

export default function Login() {
  useEffect(() => {
    document.title = "Login | Smile Artists";
  }, []);
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", background: "var(--bg-dark)" }}>
      <Header />
      <div className="login-page" style={{ flex: 1 }}>
        <div className="login-card">
          {/* Custom headers removed to use native Clerk headers */}

          <SignIn
            path="/login"
            routing="path"
            signUpUrl="/signup"
            afterSignInUrl="/post_login"
            signUpForceRedirectUrl="/post_login"
            appearance={{
              variables: {
                colorPrimary: "#d4af37",
                colorText: "#ffffff", // Brighter white
                colorBackground: "#1a1a1a",
                colorInputBackground: "#2a2a2a",
                colorInputText: "#ffffff",
                colorTextSecondary: "#cccccc", // Brighter grey
              },
              elements: {
                rootBox: {
                  width: "100%",
                  maxWidth: "420px", // Match Signup
                  margin: "0 auto",
                },
                card: {
                  background: "#1f1f1f",
                  backdropFilter: "blur(20px)", // Match Signup
                  borderRadius: "22px", // Match Signup
                  boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
                  padding: "24px", // Match Signup
                  border: "1px solid #333",
                },
                // headerTitle: { display: "none" }, // Un-hiding standard Clerk headers
                // headerSubtitle: { display: "none" },
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
