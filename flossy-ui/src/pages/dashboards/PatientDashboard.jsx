import { useEffect, useState } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { PropagateLoader } from "react-spinners";
import Header from "./DashboardHeader";
import "../../styles/patient_dashboard.css";

export default function PatientDashboard() {
  const { user, isLoaded } = useUser();
  const { session } = useSession();
  const navigate = useNavigate();

  const [pageLoading, setPageLoading] = useState(true);
  const [nextAppt, setNextAppt] = useState(null);
  const [messages, setMessages] = useState([]);
  const [aiOpen, setAiOpen] = useState(false);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);

  // 🔐 Block wrong roles
  useEffect(() => {
    if (!isLoaded) return;
    if (user?.publicMetadata?.role !== "patient") {
      navigate("/not-authorized");
    }
  }, [isLoaded, user, navigate]);

  // ---- Artificial loading + appointment fetch ----
  useEffect(() => {
    if (!isLoaded || user?.publicMetadata?.role !== "patient") return;

    setTimeout(() => {
      loadAppointment().finally(() => setPageLoading(false));
    }, 1000);
  }, [isLoaded, user]);

  async function loadAppointment() {
    const token = await session.getToken();
    const res = await fetch("http://localhost:8000/api/appointments/next", {
      headers: { Authorization: `Bearer ${token}` },
    });

    const data = await res.json();
    setNextAppt(data.appointment || null);
  }

  // 🟡 While LOADING → show only loader
  if (!isLoaded || pageLoading) {
    return (
      <>
        <Header />

        <div className="page-loader">
          <PropagateLoader color="#f0b800" size={15} />
          <p>Loading dashboard...</p>
        </div>
      </>
    );
  }

  // 🟢 Now safe to render full dashboard
  const fullName = user?.firstName || user?.fullName || "Patient";

  async function sendMessage() {
    if (!input.trim()) return;

    const msg = input;
    setInput("");
    setMessages((p) => [...p, { from: "user", text: msg }]);
    setTyping(true);

    const token = await session.getToken();
    const res = await fetch("http://localhost:8000/api/ai_response", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query: msg }),
    });

    const data = await res.json();
    setMessages((p) => [...p, { from: "ai", text: data.answer }]);
    setTyping(false);
  }

  return (
    <>
      <Header openAI={() => setAiOpen(true)} />

      <main className="patient-main">
        <h2 id="welcomeMessage">Welcome back, {fullName}!</h2>

        <div className="patient-card">
          <h3>My Dental Records</h3>
          <p>Last Visit: July 12, 2025</p>
          <button className="p-btn">View Full History</button>
        </div>

        <div className="patient-card">
          <h3>My Prescriptions</h3>
          <p>• Antiseptic Mouthwash</p>
          <button className="p-btn">Download</button>
        </div>

        <div className="patient-card">
          <h3>Upcoming Appointment</h3>

          {nextAppt ? (
            <p>
              {nextAppt.doctor_name} →{" "}
              {new Date(nextAppt.time).toLocaleString()}
            </p>
          ) : (
            <p>No upcoming appointments.</p>
          )}

          <button className="p-btn">Reschedule</button>
        </div>

        <div className="patient-card">
          <h3>AI Appointment & Care Assistant</h3>
          <p>Your smart dental partner for appointments, care & chat.</p>
          <button className="ai-open-btn" onClick={() => setAiOpen(true)}>
            💬 Chat with FlossyAI
          </button>
        </div>
      </main>

      {/* Floating AI Button */}
      <div id="open-ai-panel" onClick={() => setAiOpen(true)}>
        FlossyAI
      </div>

      {/* AI Drawer */}
      <div className={`ai-panel ${aiOpen ? "open" : ""}`}>
        <div className="ai-header">
          🎛 FlossyAI — Assistant
          <button className="close" onClick={() => setAiOpen(false)}>✖</button>
        </div>

        <div className="ai-content">
          {messages.map((m, i) => (
            <div key={i} className={m.from === "user" ? "msg-user" : "msg-ai"}>
              <b>{m.from === "user" ? "You" : "FlossyAI"}:</b> {m.text}
            </div>
          ))}

          {typing && <div className="typing">FlossyAI is typing…</div>}
        </div>

        <div className="ai-input-area">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask FlossyAI…"
          />
          <button onClick={sendMessage}>Send</button>
        </div>
      </div>
    </>
  );
}
