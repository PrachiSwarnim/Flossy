import { SignIn } from "@clerk/clerk-react";
import "../styles/login.css";

export default function Login() {
  return (
    <div className="login-page">
      <div className="login-box">
        <div className="welcome-text">
          <h1>Welcome Back!</h1>
          <p>Sign in to access your FlossyAI dashboard.</p>
        </div>

        <SignIn
          path="/login"
          routing="path"
          signUpUrl="/signup"
          afterSignInUrl="/post_login"
        />
      </div>
    </div>
  );
}
