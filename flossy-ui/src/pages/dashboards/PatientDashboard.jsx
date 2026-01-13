import { useEffect, useState } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { PropagateLoader } from "react-spinners";
// import { useVoiceAgent } from "../../hooks/useVoiceAgent"; // Legacy voice agent removed
import Header from "./DashboardHeader";
import Footer from "../../components/Footer";
import AppointmentRequestForm from "../../components/AppointmentRequestForm";
import "../../styles/patient_dashboard.css";
import "../../styles/dashboard_extras_patient.css";
import "../../styles/dashboard_modal.css";
import "../../styles/ai_features.css";
import AppointmentCard from "../../components/AppointmentCard";

import VoiceChat from "../../components/VoiceChat";


export default function PatientDashboard() {
  const { user, isLoaded } = useUser();
  const { session } = useSession();
  const navigate = useNavigate();

  const [pageLoading, setPageLoading] = useState(true);
  const [today, setToday] = useState([]);
  const [upcoming, setUpcoming] = useState([]);
  const [history, setHistory] = useState([]);
  const [followUps, setFollowUps] = useState([]);


  const [messages, setMessages] = useState([]);
  const [aiOpen, setAiOpen] = useState(false);
  const [isBookingOpen, setIsBookingOpen] = useState(false);
  const [isCallOpen, setIsCallOpen] = useState(false);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [isVoiceActive, setIsVoiceActive] = useState(false); // LiveKit Modal State
  const [myPrescriptions, setMyPrescriptions] = useState([]);

  // LOAD PRESCRIPTIONS
  async function loadPrescriptions() {
    if (!session || !user) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/prescriptions/my`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      let backendPresc = [];
      if (res.ok) {
        const data = await res.json();
        backendPresc = data.prescriptions || [];
      }

      // 🌉 BRIDGE: Load legacy localStorage prescriptions so they don't "disappear"
      const fullName = `${user.firstName || ""} ${user.lastName || ""}`.trim().toLowerCase();
      const legacyRaw = localStorage.getItem("flossy_prescriptions");
      let legacyPresc = [];

      if (legacyRaw) {
        try {
          const allLegacy = JSON.parse(legacyRaw);
          legacyPresc = allLegacy.filter(p => {
            const pName = (p.patient || "").toLowerCase();
            return pName.includes(fullName) || fullName.includes(pName);
          }).map(p => ({
            ...p,
            isLegacy: true,
            doctor: p.doctor || "Dentist",
            details: p.details,
            date: p.date
          }));
        } catch (e) { console.error("Legacy parse error", e); }
      }

      // Combine (preferring backend if there are duplicates, though legacy is local)
      setMyPrescriptions([...backendPresc, ...legacyPresc]);

    } catch (err) {
      console.error("Failed to load prescriptions", err);
    }
  }

  async function downloadPrescription(id, isLegacy = false, patientName = "") {
    if (isLegacy) {
      alert("Legacy prescriptions cannot be downloaded as PDFs yet. Please ask your doctor to re-upload this in the new system.");
      return;
    }
    if (!session) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/prescriptions/${id}/pdf`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const safeName = patientName ? patientName.replace(/[^a-zA-Z0-9]/g, "_") : "";
        a.download = `${safeName}_prescription.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } else {
        alert("Download failed.");
      }
    } catch (err) {
      console.error("Download error:", err);
    }
  }

  // VOICE AGENT
  // Legacy Hook Removed
  // const { isListening, start, stop, messages: agentMessages } = useVoiceAgent();

  // Sync voice messages to main chat
  // Sync voice messages logic removed (LiveKit handles its own state)
  // We can add a listener for LiveKit events later if needed to sync text log.

  const fullName = user ? `${user.firstName || ""} ${user.lastName || ""}`.trim() : "";

  useEffect(() => {
    if (fullName) {
      document.title = `${fullName}'s Dashboard | Smile Artists`;
    }
  }, [fullName]);

  const API = "http://localhost:8000";

  async function refreshAll() {
    console.log("🔄 AI Action detected: Refreshing Patient Dashboard...");
    await loadAppointments();
    await loadPrescriptions();
  }

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
      Promise.all([
        loadAppointments(),
        loadPrescriptions()
      ]).finally(() => setPageLoading(false));
    }, 900);

    return () => clearTimeout(timer);
  }, [isLoaded, session, user]);

  // HELPER — Remove appointments whose time already passed
  function purgePastAppointments(list) {
    const now = new Date();
    return list.filter((appt) => new Date(appt.time) > now);
  }

  // 3️⃣ AUTO-POLL APPOINTMENTS (Real-time updates for Voice Agent)
  useEffect(() => {
    if (!isLoaded || !session || user?.publicMetadata?.role !== "patient") return;

    const interval = setInterval(() => {
      // console.log("Polling appointments...");
      loadAppointments();
      loadPrescriptions();
    }, 10000); // Poll every 10 seconds

    return () => clearInterval(interval);
  }, [isLoaded, session, user]);

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
    setHistory(data.history || []);
    setFollowUps(data.follow_ups || []);
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
                  <div className="appt-doctor">{a.doctor_name}</div>
                  <div className="appt-reason">{a.reason}</div>
                  <div className="appt-status status-upcoming">Confirmed</div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <p>No upcoming appointments.</p>
                {/* Voice Assistant Modal */}
                <button className="p-btn" onClick={() => setIsBookingOpen(true)}>
                  Book Now <i className="fas fa-arrow-right"></i>
                </button>
              </div>
            )}
          </div>

          {/* FOLLOW UP REQUIRED CARD */}
          {followUps.length > 0 && (
            <div className="patient-card animate-fade-up" style={{ animationDelay: "0.15s", border: "1px solid #f0b800" }}>
              <div className="card-header">
                <h3 style={{ color: "#f0b800" }}>Follow Up Required</h3>
                <i className="fas fa-exclamation-circle card-icon" style={{ color: "#f0b800" }}></i>
              </div>
              {followUps.map(a => (
                <div key={a.id} className="appt-item" style={{ borderLeft: "3px solid #f0b800", background: "rgba(240, 184, 0, 0.05)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <b>{new Date(a.time).toLocaleDateString()}</b>
                    <span style={{ fontSize: "0.8rem", color: "#f0b800", fontWeight: "bold" }}>ACTION NEEDED</span>
                  </div>
                  <div className="appt-doctor">{a.doctor_name}</div>
                  <div className="appt-reason" style={{ marginTop: "5px" }}>
                    <i className="fas fa-info-circle"></i> Reason: <span style={{ color: "#fff" }}>{a.follow_up_reason}</span>
                  </div>
                  <div style={{ marginTop: "10px" }}>
                    <button className="p-btn small" onClick={() => setIsBookingOpen(true)} style={{ width: "100%" }}>
                      Book Follow Up
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* MEDICAL HISTORY CARD */}
          <div className="patient-card animate-fade-up" style={{ animationDelay: "0.2s" }}>
            <div className="card-header">
              <h3>Health History</h3>
              <i className="fas fa-file-medical-alt card-icon"></i>
            </div>
            {history.length > 0 ? (
              <div className="history-list" style={{ maxHeight: "250px", overflowY: "auto", paddingRight: "5px" }}>
                {history.map((a) => (
                  <div key={a.id} className="appt-item history-item" style={{ opacity: 0.7, borderLeft: "3px solid #666" }}>
                    <b>{new Date(a.time).toLocaleDateString()}</b>
                    <div className="appt-doctor" style={{ fontSize: "0.9rem" }}>{a.doctor_name}</div>
                    <div className="appt-reason" style={{ fontSize: "0.85rem" }}>{a.reason}</div>
                    <span className="history-status" style={{ fontSize: "0.75rem", color: "#aaa", textTransform: "uppercase" }}>{a.status}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="placeholder-text">No past medical history found.</p>
            )}
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
                    <button className="download-btn" onClick={() => downloadPrescription(p.id, p.isLegacy, p.patient || fullName)}>
                      <i className="fas fa-download"></i> {p.isLegacy ? "Legacy" : "Download"}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-state">No prescriptions uploaded yet.</p>
            )}
          </div>
        </div>
      </main >

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

      {/* FLOATING TRIGGER GROUP */}
      <div className="floating-group" style={{ position: "fixed", bottom: "30px", right: "30px", display: "flex", flexDirection: "row", gap: "15px", alignItems: "center", zIndex: 1000 }}>

        {/* VOICE CALL BUTTON */}
        <button
          onClick={() => setIsVoiceActive(true)}
          className="floating-action-btn btn-voice"
          title="Call Flossy"
        >
          <span>Call Flossy</span> <span className="mic-icon-anim" style={{ fontSize: "1.4rem" }}>🎤</span>
        </button>

        {/* CHAT TRIGGER */}
        <div
          id="open-ai-panel"
          onClick={() => setAiOpen(true)}
          className="floating-action-btn modern-btn"
        >
          FlossyAI
        </div>
      </div>

      {/* AI SIDE PANEL */}
      <aside className={`ai-panel ${aiOpen ? "open" : ""}`}>
        <div className="ai-header">
          <span>FlossyAI Assistant</span>
          <button className="close" onClick={() => setAiOpen(false)}>×</button>
        </div>

        {/* AI CONTENT area - Always visible now */}
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

          <button onClick={sendMessage}>Send</button>
        </div>
      </aside>

      {/* VOICE CHAT MODAL */}
      {isVoiceActive && (
        <VoiceChat
          onClose={() => setIsVoiceActive(false)}
          onAction={refreshAll}
        />
      )}

      <Footer />
    </>
  );
}

// ... helper ...

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
