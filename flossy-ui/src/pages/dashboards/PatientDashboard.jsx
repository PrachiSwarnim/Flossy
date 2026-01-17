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
  const [myPrescriptions, setMyPrescriptions] = useState([]);
  const [aiSuggestion, setAiSuggestion] = useState("Checking your history for the best recommendation...");
  const [profile, setProfile] = useState(null);

  // LOAD PRESCRIPTIONS
  async function loadPrescriptions() {
    if (!session || !user) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/prescriptions/my/`, {
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

  const API = import.meta.env.VITE_API_BASE_URL?.replace("http://", "https://");

  async function refreshAll() {
    console.log("🔄 AI Action detected: Refreshing Patient Dashboard...");
    await loadAppointments();
    await loadPrescriptions();
  }

  // 1️⃣ ROLE CHECK
  useEffect(() => {
    if (!isLoaded) return;
    const role = user?.publicMetadata?.role;
    if (role === "dentist" || role === "receptionist") {
      if (role === "dentist") navigate("/dentist");
      if (role === "receptionist") navigate("/receptionist");
    }
  }, [isLoaded, user]);

  // 1.5️⃣ LOAD AI SUGGESTION
  async function loadSuggestion() {
    if (!session) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/ai_suggestion/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAiSuggestion(data.suggestion);
      }
    } catch (e) {
      console.error("AI Suggestion error", e);
      setAiSuggestion("Ready to transform your smile? Book your <b>Initial Consultation</b> today!");
    }
  }

  async function loadProfile() {
    if (!session) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/patients/me/`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setProfile(data);
      }
    } catch (e) {
      console.error("Profile load error", e);
    }
  }


  useEffect(() => {
    if (isBookingOpen) {
      loadSuggestion();
    }
  }, [isBookingOpen]);

  // 2️⃣ LOAD APPOINTMENTS AFTER LOGIN
  useEffect(() => {
    if (!isLoaded || !session) return;

    // Allow if role is patient OR undefined (new user)
    const role = user?.publicMetadata?.role;
    if (role === "dentist" || role === "receptionist") return;

    const timer = setTimeout(() => {
      Promise.all([
        loadAppointments(),
        loadPrescriptions(),
        loadProfile()
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

    const res = await fetch(`${API}/api/appointments/patient_upcoming/`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) return;

    const data = await res.json();

    setToday(purgePastAppointments(data.today || []));
    setUpcoming(purgePastAppointments(data.upcoming || []));
    setHistory(data.history || []);
    setFollowUps(data.follow_ups || []);
  }


  // NEGOTIATION HANDLERS
  const [editAppt, setEditAppt] = useState(null);
  const [isRescheduleModalOpen, setIsRescheduleModalOpen] = useState(false);
  const [newTime, setNewTime] = useState("");

  async function handleAcceptProposal(appt) {
    if (!session) return;
    if (!window.confirm("Accept this new time?")) return;
    const token = await session.getToken({ template: "default" });
    await fetch(`${API}/api/appointments/${appt.id}`, { // Helper logic usually maps v1
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ status: "confirmed" })
    });
    loadAppointments();
  }

  function handleCounterProposal(appt) {
    setEditAppt(appt);
    setIsRescheduleModalOpen(true);
  }

  async function submitReschedule() {
    if (!newTime || !editAppt) return;
    const token = await session.getToken({ template: "default" });
    const isoDate = new Date(newTime).toISOString();

    await fetch(`${API}/api/appointments/${editAppt.id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        status: "pending_approval",
        datetime: isoDate
      })
    });

    setIsRescheduleModalOpen(false);
    setEditAppt(null);
    setNewTime("");
    loadAppointments();
    alert("Counter proposal sent! Waiting for receptionist approval.");
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

  const isNewUser = sessionStorage.getItem("flossy_is_new_user") === "true";

  return (
    <>
      <Header openAI={() => setAiOpen(true)} />

      <main className="dentist-main">
        <h2 id="welcomeMessage">{isNewUser ? "Welcome" : "Welcome back"}, {fullName}!</h2>

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

                  {/* DYNAMIC STATUS */}
                  <div className={`appt-status ${a.status === "confirmed" ? "status-upcoming" : "status-pending"}`} style={{
                    background: a.status === "negotiating" ? "#fca311" :
                      a.status === "pending_approval" ? "#888" : "",
                    color: a.status === "negotiating" ? "#000" : "#fff"
                  }}>
                    {a.status === "pending_approval" ? "Waiting Approval" :
                      a.status === "negotiating" ? "Action Needed" :
                        a.status === "confirmed" ? "Confirmed" : a.status}
                  </div>

                  {/* NEGOTIATION UI */}
                  {a.status === "negotiating" && (
                    <div style={{ marginTop: '10px', background: 'rgba(255,255,255,0.05)', padding: '10px', borderRadius: '5px' }}>
                      <p style={{ color: '#fca311', fontSize: '0.85rem', margin: '0 0 5px 0' }}>Receptionist proposed change:</p>
                      <p style={{ fontSize: '0.8rem', fontStyle: 'italic', marginBottom: '10px' }}>"{a.denial_reason}"</p>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button onClick={() => handleAcceptProposal(a)} style={{ background: '#4CAF50', border: 'none', color: '#fff', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>Accept</button>
                        <button onClick={() => handleCounterProposal(a)} style={{ background: '#fca311', border: 'none', color: '#000', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>Propose New</button>
                      </div>
                    </div>
                  )}
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
          <div className="patient-card animate-fade-up" style={{ animationDelay: "0.4s" }}>
            <div className="card-header">
              <h3>My Prescriptions</h3>
              <i className="fas fa-pills card-icon"></i>
            </div>

            {myPrescriptions.length > 0 ? (
              <div className="prescriptions-list">
                {myPrescriptions.map((p) => (
                  <div className="prescription-item" key={p.id}>
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

          {/* MY PROFILE SECTION */}
          <div className="patient-card animate-fade-up" style={{ animationDelay: "0.5s" }}>
            <div className="card-header">
              <h3>My Profile</h3>
              <i className="fas fa-user-circle card-icon"></i>
            </div>
            {profile ? (
              <div className="profile-details-list">
                <div className="profile-detail-item">
                  <span className="detail-label">Full Name</span>
                  <span className="detail-value">{profile.name}</span>
                </div>
                <div className="profile-detail-item">
                  <span className="detail-label">Email Address</span>
                  <span className="detail-value">{profile.email}</span>
                </div>
                <div className="profile-detail-item">
                  <span className="detail-label">Phone Number</span>
                  <span className="detail-value">{profile.phone || "Not provided"}</span>
                </div>
                <div style={{ display: "flex", gap: "20px" }}>
                  <div className="profile-detail-item" style={{ flex: 1 }}>
                    <span className="detail-label">Age</span>
                    <span className="detail-value">{profile.age || "N/A"}</span>
                  </div>
                  <div className="profile-detail-item" style={{ flex: 1 }}>
                    <span className="detail-label">Sex</span>
                    <span className="detail-value">{profile.sex || "N/A"}</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="placeholder-text">Loading profile...</p>
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
                  <span className="ai-label">Smile Insight:</span>
                  <p dangerouslySetInnerHTML={{ __html: aiSuggestion }}></p>
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

      {/* RESCHEDULE MODAL */}
      {isRescheduleModalOpen && (
        <div className="modal-overlay" onClick={() => setIsRescheduleModalOpen(false)}>
          <div className="modal-content" style={{ maxWidth: '400px' }} onClick={(e) => e.stopPropagation()}>
            <h3>Propose New Time</h3>
            <p style={{ margin: '10px 0', color: '#ccc' }}>The receptionist proposed: {editAppt && new Date(editAppt.time).toLocaleString()}</p>
            <p style={{ marginBottom: '5px' }}>Select your preferred time:</p>
            <input
              type="datetime-local"
              value={newTime}
              onChange={e => setNewTime(e.target.value)}
              style={{ width: '100%', padding: '10px', borderRadius: '5px', border: 'none', marginBottom: '15px' }}
            />
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button className="p-btn small" onClick={() => setIsRescheduleModalOpen(false)} style={{ background: '#555' }}>Cancel</button>
              <button className="p-btn small" onClick={submitReschedule}>Send Proposal</button>
            </div>
          </div>
        </div>
      )}

      {/* FLOATING TRIGGER GROUP */}
      <div className="floating-group" style={{ position: "fixed", bottom: "30px", right: "30px", display: "flex", flexDirection: "row", gap: "15px", alignItems: "center", zIndex: 1000 }}>

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
