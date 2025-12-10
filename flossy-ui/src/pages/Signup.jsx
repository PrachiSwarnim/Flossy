import { SignUp } from "@clerk/clerk-react";
import "../styles/signup.css";

export default function Signup() {
  return (
    <div className="signup-page">
      <div className="signup-card">
        <h1>Create Your Account</h1>
        <p>Join FlossyAI and get started.</p>

        <SignUp
          path="/signup"
          routing="path"
          signInUrl="/login"
          afterSignUpUrl="/post_login"
        />
      </div>
    </div>
  );
}
