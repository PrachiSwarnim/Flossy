import { SignIn } from "@clerk/clerk-react";
import "../styles/login.css";
import RoleHeader from "../components/RoleHeader";
import Footer from "../components/Footer";
import { useEffect } from "react";

export default function Login() {
  useEffect(() => {
    document.title = "Login | Smile Artists";
  }, []);
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <RoleHeader />
      <div className="login-page" style={{ flex: 1 }}>
        <div className="login-card">
          <h1>Welcome Back</h1>
          <p>Sign in to access your dashboard.</p>

          <SignIn
            path="/login"
            routing="path"
            signUpUrl="/signup"
            afterSignInUrl="/post_login"
            signUpForceRedirectUrl="/post_login"
            appearance={{
              elements: {
                rootBox: {
                  width: "100%",
                  maxWidth: "400px",
                  margin: "0 auto",
                },
                card: {
                  background: "rgba(255,255,255,0.95)",
                  backdropFilter: "blur(10px)",
                  borderRadius: "16px",
                  boxShadow: "none",
                  padding: "2rem",
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
