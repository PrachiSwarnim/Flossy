import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSession, useUser } from "@clerk/clerk-react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import "../styles/role_selection.css";

export default function RoleSelection() {
  const navigate = useNavigate();
  const { session } = useSession();
  const { user, isLoaded } = useUser();
  const [loading, setLoading] = useState(false);

  // 🔥 IMPORTANT: Your backend CANNOT be on Vite dev server
  const API_BASE = "http://localhost:8000"; // <-- change to your backend port

  async function pickRole(role) {
    if (!session) {
      alert("No active session found. Please log in again.");
      navigate("/login");
      return;
    }

    setLoading(true);

    try {
      // ✔ Get Clerk session token for backend verification
      const token = await session.getToken({ template: "default" });

      // ✔ Make authenticated request to backend
      const res = await fetch(`${API_BASE}/api/auth/select_role`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`, // <-- backend will verify token
        },
        body: JSON.stringify({
          role,
          userId: user.id,
          email: user.primaryEmailAddress?.emailAddress,
        }),
      });

      if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg || "Role selection failed");
      }

      // ✔ Store locally (useful for rendering dashboards instantly)
      sessionStorage.setItem("flossy_role", role);

      // ✔ Redirect to the correct dashboard
      navigate(role === "patient" ? "/patient" : "/dentist");
    } catch (err) {
      console.error("Role selection error:", err);
      alert("Could not set role. Try again.");
    } finally {
      setLoading(false);
    }
  }

  // Wait until Clerk loads
  if (!isLoaded) return <div className="center-loading">Loading…</div>;

  return (
    <>
      <Header />

      <main className="role-page">
        <section className="role-hero">
          <h1>Choose your role</h1>
          <p>Select whether you're visiting as a patient or signing in as a dental professional.</p>
        </section>

        <section className="role-grid">
          <div className="role-card" onClick={() => pickRole("patient")}>
            <h3>Patient</h3>
            <p>Book appointments, view reports, consult doctors online.</p>
          </div>

          <div className="role-card" onClick={() => pickRole("dentist")}>
            <h3>Dentist / Staff</h3>
            <p>Manage appointments, reports, and accept patient requests.</p>
          </div>
        </section>

        {loading && <div className="overlay">Applying role…</div>}
      </main>

      <Footer />
    </>
  );
}
