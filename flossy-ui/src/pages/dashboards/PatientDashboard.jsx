import { useEffect, useState } from "react";
import { useUser, useSession, useClerk } from "@clerk/clerk-react";
import Footer from "../../components/Footer";
import "../../styles/patient_dashboard.css";

export default function PatientDashboard() {
  const { user, isLoaded } = useUser();
  const { session } = useSession();
  const { signOut } = useClerk();

  const [nextAppt, setNextAppt] = useState(null);
  const [messages, setMessages] = useState([]);
  const [aiOpen, setAiOpen] = useState(false);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);

  // const API_BASE = import.meta.env.VITE_API_URL;
  const API_BASE = "http://localhost:8000"

  /* ---------------- FETCH UPCOMING APPOINTMENT ---------------- */
  useEffect(() => {
    async function loadNext() {
      if (!session) return;

      try {
        const token = await session.getToken();
        const res = await fetch(`${API_BASE}/api/appointments/next`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        const data = await res.json();
        setNextAppt(data.appointment || null);
      } catch (err) {
        console.error("Error loading appointment:", err);
      }
    }

    loadNext();
  }, [session]);

  /* ---------------- AI CHAT ---------------- */
  async function sendMessage() {
    if (!input.trim()) return;

    const userText = input;
    setInput("");
    setMessages((prev) => [...prev, { from: "user", text: userText }]);

    setTyping(true);

    try {
      const token = await session.getToken();
      const res = await fetch(`${API_BASE}/api/ai_response`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query: userText }),
      });

      const data = await res.json();
      const reply = data.answer || "No response.";
      setMessages((prev) => [...prev, { from: "ai", text: reply }]);
    } catch (err) {
      console.error("AI error:", err);
      setMessages((prev) => [...prev, { from: "ai", text: "⚠️ Error contacting FlossyAI." }]);
    } finally {
      setTyping(false);
    }
  }

  const handleEnter = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  if (!isLoaded) return <div>Loading...</div>;

  return (
    <>
      {/* HEADER — converted from HTML */}
      <header className="header">
        <div className="logo">
          <img src="/static/assets/logo.png" alt="logo" />
          <span>Smile Artists</span>
        </div>

        <nav>
          <a href="/">Home</a>
          <a href="/user">Dashboard</a>

          <button
            className="logout-btn"
            onClick={() => signOut(() => (window.location.href = "/"))}
          >
            Logout
          </button>
        </nav>
      </header>

      <main className="pd-main">
        <h2 id="welcomeMessage">
          Welcome back, {user?.firstName || "Patient"}!
        </h2>

        {/* My Dental Records */}
        <div className="card">
          <h3>My Dental Records</h3>
          <p>Last Visit: July 12, 2025</p>
          <button className="btn">View Full History</button>
        </div>

        {/* Prescriptions */}
        <div className="card">
          <h3>My Prescriptions</h3>
          <p>• Antiseptic Mouthwash</p>
          <button className="btn">Download</button>
        </div>

        {/* Upcoming Appointment */}
        <div className="card">
          <h3>Upcoming Appointment</h3>
          {!nextAppt ? (
            <p>No upcoming appointments.</p>
          ) : (
            <p>
              {nextAppt.doctor_name} —{" "}
              {new Date(nextAppt.time).toLocaleString()}
            </p>
          )}
          <button className="btn">Reschedule</button>
        </div>

        {/* AI Assistant */}
        <div className="card">
          <h3>AI Appointment & Care Assistant</h3>
          <p>Your smart dental assistant for care, questions, and voice support.</p>

          <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
            <button className="ai-btn" onClick={() => setAiOpen(true)}>
              💬 Chat
            </button>
          </div>
        </div>
      </main>

      {/* AI PANEL */}
      <button className="ai-tab" onClick={() => setAiOpen(true)}>
        FlossyAI
      </button>

      <div className={`ai-panel ${aiOpen ? "open" : ""}`}>
        <div className="ai-header">
          🎛 FlossyAI — Assistant
          <span className="close-btn" onClick={() => setAiOpen(false)}>✖</span>
        </div>

        <div className="ai-content">
          {messages.map((m, i) => (
            <div key={i} className={m.from === "user" ? "msg-user" : "msg-ai"}>
              <b>{m.from === "user" ? "You" : "FlossyAI"}:</b> {m.text}
            </div>
          ))}

          {typing && (
            <div className="typing">
              <span className="typing-dots">FlossyAI is typing</span>
            </div>
          )}
        </div>

        <div className="ai-input-area">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleEnter}
            placeholder="Ask about appointments, prescriptions, or say hello..."
          />
          <button onClick={sendMessage}>Send</button>
        </div>
      </div>

      <Footer />
    </>
  );
}
