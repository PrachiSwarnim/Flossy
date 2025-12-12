import { useEffect } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import Header from "../components/RoleHeader";

export default function PostLogin() {
  const { user, isLoaded } = useUser();
  const { session } = useSession();
  const navigate = useNavigate();

  useEffect(() => {
    // Wait for Clerk hydration to finish
    if (!isLoaded || !session || !user) return;

    const setup = async () => {
      const token = await session.getToken({ template: "default" });

      sessionStorage.setItem("flossy_token", token);
      sessionStorage.setItem("flossy_user", JSON.stringify(user));

      // 1️⃣ Clerk metadata role
      const clerkRole = user.publicMetadata?.role;

      if (clerkRole === "patient") {
        navigate("/patient");
        return;
      }

      if (clerkRole === "dentist") {
        navigate("/dentist");
        return;
      }

      // 2️⃣ Backend role fallback
      try {
        const res = await fetch("http://localhost:8000/api/auth/post_login", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        const data = await res.json();
        const backendRole = data?.user?.role;

        if (backendRole === "patient") {
          navigate("/patient");
          return;
        }

        if (backendRole === "dentist") {
          navigate("/dentist");
          return;
        }
      } catch (err) {
        console.error("Backend post_login error:", err);
      }

      // 3️⃣ No role → go to role selection
      navigate("/role_selection");
    };

    setup();
  }, [isLoaded, session, user, navigate]);

  return (
    <div style={{ padding: "0", textAlign: 'center', background: "var(--bg-dark)", minHeight: "100vh", color: "var(--primary-gold)" }}>
      <Header />
      <div style={{ marginTop: "5rem" }}>
        <h2>Setting up your account…</h2>
      </div>
    </div>
  );
}
