import { useEffect, useState } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { PropagateLoader } from "react-spinners";
import { useVoiceAgent } from "../../hooks/useVoiceAgent";
import Header from "./DashboardHeader";
import Footer from "../../components/Footer";
import AppointmentRequestForm from "../../components/AppointmentRequestForm";
import "../../styles/patient_dashboard.css";
import "../../styles/dashboard_extras_patient.css";
import "../../styles/dashboard_modal.css";
import "../../styles/ai_features.css";

export default function PatientDashboard() {
  const { user, isLoaded } = useUser();
  const { session } = useSession();
  const navigate = useNavigate();

  const [pageLoading, setPageLoading] = useState(true);
  const [today, setToday] = useState([]);
  const [upcoming, setUpcoming] = useState([]);

  const [messages, setMessages] = useState([]);
  const [aiOpen, setAiOpen] = useState(false);
  const [isBookingOpen, setIsBookingOpen] = useState(false);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [myPrescriptions, setMyPrescriptions] = useState([]);

  // LOAD PRESCRIPTIONS (Simulated Backend)
  useEffect(() => {
    if (!user) return;
    const fullName = `${user.firstName || ""} ${user.lastName || ""}`.trim();

    // Poll for new prescriptions (Simulating real-time)
    const interval = setInterval(() => {
      try {
        const allPresc = JSON.parse(localStorage.getItem("flossy_prescriptions") || "[]");
        console.log("Checking prescriptions:", allPresc.length, "for user:", fullName);

        const mine = allPresc.filter(p => {
          if (!p.patient) return false; // Skip invalid entries
          const pName = p.patient.toLowerCase();
          const fName = fullName.toLowerCase();
          return pName.includes(fName) || fName.includes(pName);
        });

        console.log("Found matches:", mine.length);
        setMyPrescriptions(mine);
      } catch (err) {
        console.error("Error loading prescriptions:", err);
      }
    }, 2000); // Check every 2s

    return () => clearInterval(interval);
  }, [user]);

  // VOICE AGENT
  const { isListening, start, stop, messages: agentMessages } = useVoiceAgent();

  // Sync voice messages to main chat
  useEffect(() => {
    // This is a simple merge strategy. In a real app, we might want to unify the source of truth.
    // For now, we just ensure that if the agent sends a message, it appears.
    // We only take the *latest* if it's new. 
    // Actually, let's just combine them in the render or simpler: 
    // We'll rely on the user to use one mode or the other mostly, but...
    // Let's just append new agent messages to the local state (deduplication might be needed).

    // BETTER STRATEGY: 
    // If agentMessages changes, we look at the last one.
    const lastMsg = agentMessages[agentMessages.length - 1];
    if (lastMsg) {
      setMessages(prev => {
        // avoid duplicates if possible (simple check)
        if (prev.length > 0 && prev[prev.length - 1].text === lastMsg.text) return prev;
        return [...prev, lastMsg];
      });
    }
  }, [agentMessages]);

  const fullName = user ? `${user.firstName || ""} ${user.lastName || ""}`.trim() : "";

  useEffect(() => {
    if (fullName) {
      document.title = `${fullName}'s Dashboard | Smile Artists`;
    }
  }, [fullName]);

  const API = "http://localhost:8000";

  // 1️⃣ ROLE CHECK
  useEffect(() => {
    if (!isLoaded) return;
    if (user && user.publicMetadata?.role !== "patient") {
      navigate("/not-authorized");
    }
  }, [isLoaded, user]);

  // 2️⃣ LOAD APPOINTMENTS AFTER LOGIN
  useEffect(() => {
    if (!isLoaded || !session) return;
    if (user?.publicMetadata?.role !== "patient") return;

    const timer = setTimeout(() => {
      loadAppointments().finally(() => setPageLoading(false));
    }, 900);

    return () => clearTimeout(timer);
  }, [isLoaded, session, user]);

  // HELPER — Remove appointments whose time already passed
  function purgePastAppointments(list) {
    const now = new Date();
    return list.filter((appt) => new Date(appt.time) > now);
  }

  // Auto-purge past appointments every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setToday((prev) => purgePastAppointments(prev));
      setUpcoming((prev) => purgePastAppointments(prev));
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // LOAD APPOINTMENTS
  async function loadAppointments() {
    if (!session) return;

    const token = await session.getToken({ template: "default" });

    const res = await fetch(`${API}/api/appointments/patient_upcoming`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) return;

    const data = await res.json();

    setToday(purgePastAppointments(data.today || []));
    setUpcoming(purgePastAppointments(data.upcoming || []));
  }

  // AI CHAT HANDLER
  async function sendMessage() {
    if (!input.trim()) return;
    if (!session) return;

    const msg = input;
    setInput("");

    // INTERCEPT: If user asks to book a cleaning via chip
    if (msg === "Book a cleaning") {
      setMessages(prev => [...prev, { from: "user", text: msg }]);
      setTimeout(() => {
        setMessages(prev => [...prev, { from: "ai", text: "I can help with that! Opening the booking form for you..." }]);
        setIsBookingOpen(true); // Open the modal
      }, 500);
      return;
    }

    setMessages((prev) => [...prev, { from: "user", text: msg }]);
    setTyping(true);

    const token = await session.getToken({ template: "default" });

    const aiRes = await fetch(`${API}/api/ai_response`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query: msg }),
    });

    const aiData = await aiRes.json();

    setMessages((prev) => [...prev, { from: "ai", text: aiData.answer }]);
    setTyping(false);

    loadAppointments();
  }

  // LOADING SCREEN
  const loadingScreen = (
    <>
      <Header />
      <div className="page-loader">
        <PropagateLoader color="#f0b800" size={15} />
        <p>Loading dashboard...</p>
      </div>
    </>
  );

  if (!isLoaded || !session || pageLoading || !user) {
    return loadingScreen;
  }

  // Removed misplaced hook from here

  return (
    <>
      <Header openAI={() => setAiOpen(true)} />

      <main className="dentist-main">
        <h2 id="welcomeMessage">Welcome back, {fullName}!</h2>

        <div className="patient-grid">
          {/* APPOINTMENTS CARD */}
          <div className="patient-card animate-fade-up" style={{ animationDelay: "0.1s" }}>
            <div className="card-header">
              <h3>Upcoming Appointments</h3>
              <i className="fas fa-calendar-alt card-icon"></i>
            </div>
            {upcoming.length > 0 ? (
              upcoming.map((a) => (
                <div key={a.id} className="appt-item">
                  <b>{formatApptTime(a.time)}</b>
                  <div className="appt-doctor">Dr. {a.doctor_name}</div>
                  <div className="appt-reason">{a.reason}</div>
                  <div className="appt-status status-upcoming">Confirmed</div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <p>No upcoming appointments.</p>
                <button className="p-btn" onClick={() => setIsBookingOpen(true)}>
                  Book Now <i className="fas fa-arrow-right"></i>
                </button>
              </div>
            )}
          </div>

          {/* MEDICAL HISTORY CARD */}
          <div className="patient-card animate-fade-up" style={{ animationDelay: "0.2s" }}>
            <div className="card-header">
              <h3>Health History</h3>
              <i className="fas fa-file-medical-alt card-icon"></i>
            </div>
            <p className="placeholder-text">View your past treatments and records.</p>
            <button className="p-btn secondary">View History</button>
          </div>

          {/* AI INSIGHTS CARD */}
          <div className="patient-card animate-fade-up" style={{ animationDelay: "0.3s", gridColumn: "1 / -1" }}>
            <div className="card-header">
              <h3>My Oral Health</h3>
              <i className="fas fa-smile-beam card-icon"></i>
            </div>
            <div className="info-box success">
              <i className="fas fa-check-circle"></i>
              <span>Your gum health score is excellent! Keep flossing.</span>
            </div>
          </div>

          {/* PRESCRIPTIONS CARD */}
          <div className="patient-card animate-fade-up" style={{ animationDelay: "0.4s", gridColumn: "span 2" }}>
            <div className="card-header">
              <h3>My Prescriptions</h3>
              <i className="fas fa-pills card-icon"></i>
            </div>

            {myPrescriptions.length > 0 ? (
              <div className="prescriptions-list">
                {myPrescriptions.map((p) => (
                  <div className="prescription-item" key={p.id}>
                    <div className="presc-icon">
                      <i className="fas fa-file-medical"></i>
                    </div>
                    <div className="presc-info">
                      <h4>Prescribed by Dr. {p.doctor || "Dentist"}</h4>
                      <span className="presc-date">{new Date(p.date).toLocaleDateString()}</span>
                      <p className="presc-details">{p.details}</p>
                    </div>
                    <button className="download-btn">
                      <i className="fas fa-download"></i> Download
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-state">No prescriptions uploaded yet.</p>
            )}
          </div>
        </div>
      </main>

      {/* BOOKING MODAL */}
      {
        isBookingOpen && (
          <div className="modal-overlay" onClick={() => setIsBookingOpen(false)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <button className="modal-close" onClick={() => setIsBookingOpen(false)}>×</button>

              {/* FLOSSY AI SMART SUGGESTION */}
              <div className="flossy-ai-suggestion">
                <div className="ai-avatar">AI</div>
                <div className="ai-text">
                  <span className="ai-label">FlossyAI Suggestion:</span>
                  <p>
                    Based on your history, it's been 6 months since your last cleaning.
                    Would you like to book a <span className="highlight">Routine Check-up & Cleaning</span>?
                  </p>
                </div>
              </div>

              <div className="modal-form-wrapper">
                <h3>Book Your Appointment</h3>
                <AppointmentRequestForm className="dashboard-form" />
              </div>
            </div>
          </div>
        )
      }

      {/* FLOATING TRIGGER */}
      <div id="open-ai-panel" onClick={() => setAiOpen(true)}>
        FlossyAI
      </div>

      {/* AI SIDE PANEL */}
      <aside className={`ai-panel ${aiOpen ? "open" : ""}`}>
        <div className="ai-header">
          <span>FlossyAI Assistant</span>
          <button className="close" onClick={() => setAiOpen(false)}>×</button>
        </div>

        <div className="ai-content">
          {messages.length === 0 && (
            <div className="ai-welcome">
              <p>
                Hi <b>{user.firstName}</b>!
                {upcoming.length > 0
                  ? " You have an upcoming appointment. Do you have any questions about it?"
                  : " How can I help you with your dental health today?"}
              </p>

              <div className="ai-chips">
                <button onClick={() => setInput("I have a toothache") || sendMessage()}>🦷 Toothache</button>
                <button onClick={() => setInput("Cost of dental implants") || sendMessage()}>💰 Pricing</button>
                <button onClick={() => setInput("Book a cleaning") || sendMessage()}>📅 Book Cleaning</button>
                <button onClick={() => setInput("Post-op care instructions") || sendMessage()}>🩹 Post-op Care</button>
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={m.from === "ai" ? "msg-ai" : "msg-user"}>
              <b>{m.from === "ai" ? "FlossyAI" : "You"}:</b> {m.text}
            </div>
          ))}
          {typing && <div className="typing">FlossyAI is typing<span className="dot-one">.</span><span className="dot-two">.</span><span className="dot-three">.</span></div>}
        </div>

        <div className="ai-input-area">
          <input
            type="text"
            placeholder="Ask something..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          />
          <button
            onClick={isListening ? stop : start}
            title={isListening ? "Stop Speaking" : "Start Voice Agent"}
            style={{ background: isListening ? "#ff4d4d" : "#ffcb05" }}
          >
            {isListening ? "🛑" : "🎤"}
          </button>
          <button onClick={sendMessage}>Send</button>
        </div>
      </aside>

      <Footer />
    </>
  );
}

// Formatting Helper
function formatApptTime(t) {
  return (
    new Date(t).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }) +
    " • " +
    new Date(t)
      .toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      })
      .replace("am", "AM")
      .replace("pm", "PM")
  );
}
