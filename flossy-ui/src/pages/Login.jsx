import { SignIn } from "@clerk/clerk-react";
import "../styles/login.css";
import Header from "../components/RoleHeader";
import Footer from "../components/Footer";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { Meteors } from "../components/ui/Meteors";

export default function Login() {
  useEffect(() => {
    document.title = "Login | Smile Artists";
  }, []);
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", background: "#0f0f0f" }}>
      <Header />
      <div className="login-page relative overflow-hidden" style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "4rem 1rem" }}>
        
        {/* Animated Background Elements */}
        <Meteors number={15} />
        <div
          className="absolute top-1/4 left-1/4 w-[500px] h-[500px] pointer-events-none opacity-40"
          style={{
            background: "radial-gradient(circle at center, rgba(212,175,55,0.08) 0%, transparent 60%)",
          }}
        />

        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="login-card relative z-10 w-full max-w-md"
        >
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
        </motion.div>
      </div>
      <Footer />
    </div>
  );
}
