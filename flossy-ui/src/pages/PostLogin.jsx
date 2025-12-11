import { useEffect } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";

export default function PostLogin() {
  const { user, isLoaded } = useUser();
  const { session } = useSession();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoaded) return;

    if (!user) {
      navigate("/login");
      return;
    }

    const setup = async () => {
      const token = await session.getToken();
      sessionStorage.setItem("flossy_token", token);
      sessionStorage.setItem("flossy_user", JSON.stringify(user));

      // ------------------------------------------------------------------
      // 1️⃣ Read Clerk metadata role FIRST (fastest & authoritative)
      // ------------------------------------------------------------------
      const clerkRole = user.publicMetadata?.role;

      if (clerkRole === "patient") {
        navigate("/patient");
        return;
      } else if (clerkRole === "dentist") {
        navigate("/dentist");
        return;
      }

      // ------------------------------------------------------------------
      // 2️⃣ If role NOT in Clerk metadata (first-time login), fetch from backend
      // ------------------------------------------------------------------
      try {
        const res = await fetch("http://localhost:8000/api/auth/post_login", {
          headers: { Authorization: `Bearer ${token}` }
        });

        const data = await res.json();
        const backendRole = data?.user?.role;

        if (backendRole === "patient") {
          navigate("/patient");
          return;
        } else if (backendRole === "dentist") {
          navigate("/dentist");
          return;
        }
      } catch (err) {
        console.error("Backend post_login failed:", err);
      }

      // ------------------------------------------------------------------
      // 3️⃣ No role anywhere → send to role selection
      // ------------------------------------------------------------------
      navigate("/role_selection");
    };

    setup();
  }, [isLoaded, session, user, navigate]);

  return (
    <div style={{ padding: "5rem", textAlign: "center" }}>
      <h2>Setting up your account…</h2>
    </div>
  );
}
