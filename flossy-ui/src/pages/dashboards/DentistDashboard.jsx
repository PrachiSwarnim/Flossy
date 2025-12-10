import { useEffect, useState } from "react";
import {
  useUser,
  useSession,
  useClerk,
  SignedIn,
  UserButton
} from "@clerk/clerk-react";
import { Link } from "react-router-dom";
import Footer from "../../components/Footer";
import "../../styles/dentist_dashboard.css";

export default function DentistDashboard() {
  const { user } = useUser();
  const { session } = useSession();
  const { signOut } = useClerk();

  const [today, setToday] = useState([]);
  const [upcoming, setUpcoming] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [aiOpen, setAiOpen] = useState(false);

  const API_BASE = "http://localhost:8000";

  const tokenPromise = async () => await session.getToken();

  const fullName = `${user?.firstName || ""} ${user?.lastName || ""}`.trim();
  const dentistName = `Dr. ${fullName}`;

  /* ---------------- FETCH APPOINTMENTS ---------------- */
  async function loadAppointments() {
    const token = await tokenPromise();
    const res = await fetch(`${API_BASE}/api/appointments/dentist_upcoming`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    const data = await res.json();
    setToday(data.today || []);
    setUpcoming(data.upcoming || []);
  }

  /* ---------------- MARK COMPLETED ---------------- */
  async function markCompleted(id) {
    const token = await session.getToken();
    await fetch(`${API_BASE}/api/appointments/mark_completed/${id}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    loadAppointments();
  }

  /* ---------------- FLOSSYAI CHAT ---------------- */
  async function sendMessage() {
    if (!input.trim()) return;

    const userText = input;
    setInput("");

    const token = await tokenPromise();

    setMessages((prev) => [...prev, { from: "user", text: userText }]);

    try {
      const res = await fetch(`${API_BASE}/api/doctor_ai/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query: userText }),
      });

      const data = await res.json();

      setMessages((prev) => [...prev, { from: "ai", text: data.answer }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { from: "ai", text: "⚠️ Error connecting to FlossyAI." },
      ]);
    }
  }

  const handleEnter = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  /* ---------------- LOAD ON START ---------------- */
  useEffect(() => {
    if (user) loadAppointments();
  }, [user]);

  return (
    <>
      {/* ⭐ NEW DASHBOARD HEADER — clean & focused */}
      <header className="dashboard-header">
        <div className="dash-logo">
          <Link to="/">🦷 Smile Artists Dashboard</Link>
        </div>

        <div className="dash-actions">
          <SignedIn>
            <button
              className="logout-btn"
              onClick={() => signOut(() => (window.location.href = "/"))}
            >
              Logout
            </button>

            <UserButton afterSignOutUrl="/" />
          </SignedIn>
        </div>
      </header>

      {/* ⭐ REST OF DASHBOARD REMAINS SAME */}
      <div className="dentist-page">
        <div className="dentist-container">
          <h1 className="welcome-title">Welcome back, {dentistName}!</h1>

          <div className="dashboard-grid">
            <div className="card">
              <h3>Today’s Appointments</h3>
              {today.length === 0 ? (
                <p>No appointments today.</p>
              ) : (
                today.map((a) => (
                  <div key={a.id} className="appt-box">
                    <b>
                      {new Date(a.time).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </b>
                    <p><strong>{a.patient_name}</strong></p>
                    <p>Reason: {a.reason}</p>
                    <p>Phone: {a.phone}</p>

                    <button className="btn-complete" onClick={() => markCompleted(a.id)}>
                      Mark Completed
                    </button>

                    <button className="btn-call" onClick={() => (window.location.href = `tel:${a.phone}`)}>
                      Call Patient
                    </button>
                  </div>
                ))
              )}
            </div>

            <div className="card">
              <h3>Recent Interactions</h3>
              <p>Loading…</p>
            </div>

            <div className="card">
              <h3>AI Insights</h3>
              <p>FlossyAI detected gum disease risk cases this week.</p>
              <p className="link">View Report</p>
            </div>

            <div className="card">
              <h3>Notifications</h3>
              <p>2 new appointment requests pending approval.</p>
              <p className="link">Review Now</p>
            </div>
          </div>
        </div>
      </div>

      {/* ⭐ AI PANEL */}
      <button className="ai-tab" onClick={() => setAiOpen(true)}>FlossyAI</button>

      <div className={`ai-panel ${aiOpen ? "open" : ""}`}>
        <div className="ai-header">
          🦷 FlossyAI Assistant
          <span className="close-btn" onClick={() => setAiOpen(false)}>✖</span>
        </div>

        <div className="ai-content">
          {messages.map((m, i) => (
            <div key={i} className={m.from === "user" ? "msg-user" : "msg-ai"}>
              <b>{m.from === "user" ? "You" : "FlossyAI"}:</b> {m.text}
            </div>
          ))}
        </div>

        <div className="ai-input-area">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleEnter}
            placeholder="Ask FlossyAI…"
          />
          <button onClick={sendMessage}>Send</button>
        </div>
      </div>

      <Footer />
    </>
  );
}
