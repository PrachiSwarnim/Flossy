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
      // Get token - try with template first, fallback to without template
      let token;
      try {
        token = await session.getToken({ template: "default" });
      } catch (templateErr) {
        console.warn("Token template 'default' failed, trying without template:", templateErr);
        token = await session.getToken();
      }

      if (!token) {
        console.error("Failed to get authentication token");
        navigate("/patient"); // Fallback
        return;
      }

      sessionStorage.setItem("flossy_token", token);
      sessionStorage.setItem("flossy_user", JSON.stringify(user));

      // 0️⃣ Determine if First Login or Return Login
      // If lastSignInAt is very close to createdAt, it's likely a fresh signup.
      const createdAt = new Date(user.createdAt).getTime();
      const lastSignInAt = new Date(user.lastSignInAt).getTime();
      const isNewUser = !user.lastSignInAt || (Math.abs(lastSignInAt - createdAt) < 30000); // 30 sec threshold
      sessionStorage.setItem("flossy_is_new_user", isNewUser ? "true" : "false");

      const API = import.meta.env.VITE_API_BASE_URL;

      // 1️⃣ Backend Role Sync & Check
      // We prioritize the backend response because it contains the authoritative role logic and ensures the DB is synced.
      try {
        console.log("Calling post_login with token:", token.substring(0, 30) + "...");
        const res = await fetch(`${API}/api/auth/post_login`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            email_hint: user.primaryEmailAddress?.emailAddress,
            first_name: user.firstName || "",
            last_name: user.lastName || ""
          })
        });

        if (res.ok) {
          const data = await res.json();
          const role = data?.user?.role || "patient";
          const email = user.primaryEmailAddress?.emailAddress?.toLowerCase();

          console.log(`🎯 Backend confirmed role: ${role} for ${email}`);

          if (role === "dentist") {
            sessionStorage.setItem("flossy_role", "dentist");
            navigate("/dentist");
            return;
          }
          if (role === "receptionist") {
            navigate("/receptionist");
            return;
          }

          // If it's patient, go to patient
          navigate("/patient");
          return;
        } else {
          console.error("post_login failed with status:", res.status);
          const errorData = await res.text();
          console.error("Error details:", errorData);
          // Fallback to patient if sync failed but user is authenticated in Clerk
          sessionStorage.setItem("flossy_role", "patient");
          navigate("/patient");
          return;
        }
      } catch (err) {
        console.error("Backend post_login error:", err);
        sessionStorage.setItem("flossy_role", "patient");
        navigate("/patient");
      }
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
