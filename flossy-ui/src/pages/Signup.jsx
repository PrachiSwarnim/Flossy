import { SignUp } from "@clerk/clerk-react";
import "../styles/signup.css";

export default function Signup() {
  return (
    <div className="signup-page">
      <div className="signup-card">
        <h1>Create Your Account</h1>
        <p>Welcome! Please fill in the details to get started.</p>

        <SignUp
          path="/signup"
          routing="path"
          signInUrl="/login"
          forceRedirectUrl="/post_login"
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
            },
          }}
        />

      </div>
    </div>
  );
}
