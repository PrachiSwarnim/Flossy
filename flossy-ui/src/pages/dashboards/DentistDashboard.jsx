import { useEffect, useState } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { PropagateLoader } from "react-spinners";
import { useVoiceAgent } from "../../hooks/useVoiceAgent";
import Header from "./DashboardHeader";
import Footer from "../../components/Footer";
import "../../styles/dentist_dashboard.css";
import "../../styles/dashboard_extras.css";

export default function DentistDashboard() {
  const { user, isLoaded } = useUser();
  const { session } = useSession();
  const navigate = useNavigate();

  // 🔒 BLOCK ACCESS UNTIL LOADED
  useEffect(() => {
    if (!isLoaded) return;

    const role = user?.publicMetadata?.role;

    if (role !== "dentist") {
      navigate("/not-authorized");
    }
  }, [isLoaded, user, navigate]);

  // === Missing State (RESTORED) ===
  const [pageLoading, setPageLoading] = useState(true);
  const [today, setToday] = useState([]);
  const [upcoming, setUpcoming] = useState([]);
  const [aiOpen, setAiOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);

  // Follow Up State
  const [followUpOpen, setFollowUpOpen] = useState(false);
  const [selectedApptId, setSelectedApptId] = useState(null);
  const [followUpReason, setFollowUpReason] = useState("");

  // VOICE AGENT (Legacy Disabled)
  const isListening = false;
  const start = () => alert("Voice Agent migrated to Patient Dashboard.");
  const stop = () => { };
  const agentMessages = [];

  // Sync voice messages to main chat
  useEffect(() => {
    const lastMsg = agentMessages[agentMessages.length - 1];
    if (lastMsg) {
      setMessages(prev => {
        if (prev.length > 0 && prev[prev.length - 1].text === lastMsg.text) return prev;
        return [...prev, lastMsg];
      });
    }
  }, [agentMessages]);

  const API = "http://localhost:8000";

  // === Fetch Appointments ===
  async function loadAppointments() {
    const token = await session.getToken({ template: "default" });
    const res = await fetch(`${API}/api/appointments/dentist_upcoming`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    const data = await res.json();

    // Filter out appointments strictly before today (local time)
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());

    const validToday = (data.today || []).filter(a => new Date(a.time) >= startOfToday);
    const validUpcoming = (data.upcoming || []).filter(a => new Date(a.time) >= startOfToday);

    setToday(validToday);
    setUpcoming(validUpcoming);
  }

  // === Artificial Delay + Load Data ===
  useEffect(() => {
    if (!isLoaded || user?.publicMetadata?.role !== "dentist") return;

    setTimeout(() => {
      loadAppointments().finally(() => setPageLoading(false));
    }, 1000);
  }, [isLoaded, user]);

  // === Full Name ===
  const fullName =
    `${user?.firstName || ""} ${user?.lastName || ""}`.trim() || "Doctor";

  useEffect(() => {
    if (fullName) {
      document.title = `Dr. ${fullName} | Smile Artists Dental Studio`;
    }
  }, [fullName]);

  async function markCompleted(id) {
    const token = await session.getToken({ template: "default" });

    await fetch(`${API}/api/appointments/mark_completed/${id}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`
      }
    });

    // Refresh appointment list
    loadAppointments();
  }

  async function markFollowUp() {
    if (!followUpReason) return alert("Please enter a reason for follow-up.");

    const token = await session.getToken({ template: "default" });
    await fetch(`${API}/api/appointments/mark_completed/${selectedApptId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ follow_up_reason: followUpReason })
    });

    setFollowUpOpen(false);
    setFollowUpReason("");
    setSelectedApptId(null);
    loadAppointments();
  }

  function openFollowUpModal(id) {
    setSelectedApptId(id);
    setFollowUpOpen(true);
  }


  function capitalizeFullName(name) {
    if (!name) return "";
    return name
      .trim()
      .split(/\s+/)
      .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(" ");
  }


  // === Prescription State ===
  const [prescPatient, setPrescPatient] = useState("");
  const [prescDetails, setPrescDetails] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [patientsList, setPatientsList] = useState([]);

  // Load Real Patients from DB
  useEffect(() => {
    if (!isLoaded || !session) return;

    async function fetchPatients() {
      try {
        const token = await session.getToken({ template: "default" });
        const res = await fetch(`${API}/api/patients`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (res.ok) {
          const data = await res.json();
          setPatientsList(data);
        }
      } catch (err) {
        console.error("Failed to load patients", err);
      }
    }

    fetchPatients();
  }, [isLoaded, session]);

  // === Handle Prescription Upload ===
  function handlePrescriptionUpload() {
    if (!prescPatient || !prescDetails) {
      alert("Please select a patient and enter prescription details.");
      return;
    }

    setIsUploading(true);

    // Simulate network delay
    setTimeout(() => {
      const newPrescription = {
        id: Date.now(),
        patient: prescPatient, // This is the name string
        doctor: fullName,
        date: new Date().toISOString(),
        details: prescDetails,
        fileName: "prescription_" + Date.now() + ".pdf" // Mock file
      };

      // Save to Simulated DB (LocalStorage)
      const existing = JSON.parse(localStorage.getItem("flossy_prescriptions") || "[]");
      const updated = [newPrescription, ...existing];
      localStorage.setItem("flossy_prescriptions", JSON.stringify(updated));

      // Reset Form
      setPrescPatient("");
      setPrescDetails("");
      setIsUploading(false);
      alert(`Prescription uploaded successfully for ${prescPatient}!`);
    }, 1500);
  }

  // === AI Chat ===
  async function sendMessage() {
    if (!input.trim()) return;

    const text = input;
    setInput("");
    setMessages((prev) => [...prev, { from: "user", text }]);
    setTyping(true);

    const token = await session.getToken();
    const res = await fetch(`${API}/api/doctor_ai/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query: text }),
    });

    const data = await res.json();
    setMessages((prev) => [...prev, { from: "ai", text: data.answer }]);
    setTyping(false);
  }

  // 🔄 STILL LOADING → show loader only
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

  // === Render Dashboard ===
  return (
    <>
      <Header openAI={() => setAiOpen(true)} />

      <main className="dentist-main">
        <h2 id="welcomeMessage">Welcome back, Dr. {fullName}!</h2>

        <div className="grid">
          <div className="card animate-fade-up" style={{ animationDelay: "0.1s" }}>
            <div className="card-header">
              <h3>Today’s Appointments</h3>
              <i className="fas fa-calendar-check card-icon"></i>
            </div>
            {today.length ? (
              today.map((a) => (
                <div className="appt-item" key={a.id}>
                  <b>
                    {new Date(a.time).toLocaleTimeString("en-IN", {
                      hour: "2-digit",
                      minute: "2-digit",
                      hour12: true
                    })}
                  </b>
                  <div className="appt-patient">{capitalizeFullName(a.patient_name)}</div>
                  <div className="appt-reason">{a.reason}</div>

                  {/* 🔥 Buttons */}
                  {a.status !== "completed" && a.status !== "follow_up" && (
                    <div className="action-buttons" style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                      <button className="done-btn" onClick={() => markCompleted(a.id)}>
                        Mark Completed
                      </button>
                      <button className="follow-up-btn"
                        style={{ background: "#f0b800", color: "#000", border: "none", padding: "5px 10px", borderRadius: "5px", cursor: "pointer", fontWeight: "bold" }}
                        onClick={() => openFollowUpModal(a.id)}>
                        Follow Up
                      </button>
                    </div>
                  )}

                  {a.status === "completed" && (
                    <span className="completed-tag">Completed <i className="fas fa-check-circle"></i></span>
                  )}

                  {a.status === "follow_up" && (
                    <div className="follow-up-tag" style={{ color: "#f0b800", marginTop: "5px" }}>
                      <i className="fas fa-clock"></i> Follow Up Required
                      <div style={{ fontSize: "0.8rem", opacity: 0.8 }}>Note: {a.follow_up_reason}</div>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p className="empty-state">No appointments remaining today.</p>
            )}
          </div>

          {/* UPCOMING APPOINTMENTS (New Section) */}
          <div className="card animate-fade-up" style={{ animationDelay: "0.15s" }}>
            <div className="card-header">
              <h3>Upcoming Appointments</h3>
              <i className="fas fa-calendar-alt card-icon"></i>
            </div>
            {upcoming.length ? (
              upcoming.map((a) => (
                <div className="appt-item" key={a.id} style={{ opacity: 0.8 }}>
                  <b>
                    {new Date(a.time).toLocaleDateString()} {new Date(a.time).toLocaleTimeString("en-IN", {
                      hour: "2-digit",
                      minute: "2-digit",
                      hour12: true
                    })}
                  </b>
                  <div className="appt-patient">{capitalizeFullName(a.patient_name)}</div>
                  <div className="appt-reason">{a.reason}</div>
                  <div className="appt-status status-upcoming">Scheduled</div>
                </div>
              ))
            ) : (
              <p className="empty-state">No upcoming appointments.</p>
            )}
          </div>


          <div className="card animate-fade-up" style={{ animationDelay: "0.2s" }}>
            <div className="card-header">
              <h3>Recent Interactions</h3>
              <i className="fas fa-history card-icon"></i>
            </div>
            <p className="placeholder-text">Checking patient history...</p>
          </div>

          <div className="card animate-fade-up" style={{ animationDelay: "0.3s" }}>
            <div className="card-header">
              <h3>AI Insights</h3>
              <i className="fas fa-brain card-icon"></i>
            </div>
            <div className="info-box warning">
              <i className="fas fa-exclamation-triangle"></i>
              <span>FlossyAI detected gum disease risk this week.</span>
            </div>
          </div>

          <div className="card animate-fade-up" style={{ animationDelay: "0.4s" }}>
            <div className="card-header">
              <h3>Notifications</h3>
              <i className="fas fa-bell card-icon"></i>
            </div>
            <div className="info-box info">
              <i className="fas fa-info-circle"></i>
              <span>2 new appointment requests pending approval.</span>
            </div>
          </div>

          {/* PRESCRIPTION CARD */}
          <div className="card animate-fade-up" style={{ animationDelay: "0.5s", gridColumn: "span 2" }}>
            <div className="card-header">
              <h3>Prescribe Medicine</h3>
              <i className="fas fa-file-prescription card-icon"></i>
            </div>
            <div className="prescription-form">
              <div className="form-group">
                <label>Select Patient</label>
                <select
                  value={prescPatient}
                  onChange={(e) => setPrescPatient(e.target.value)}
                  className="dashboard-select"
                >
                  <option value="">-- Choose Patient --</option>
                  {patientsList.length > 0 ? (
                    patientsList.map(p => (
                      <option key={p.id} value={p.name}>{capitalizeFullName(p.name)}</option>
                    ))
                  ) : (
                    <option disabled>Loading patients...</option>
                  )}
                </select>
              </div>

              <div className="form-group">
                <label>Prescription Details / Notes</label>
                <textarea
                  placeholder="e.g. Amoxicillin 500mg, twice daily..."
                  value={prescDetails}
                  onChange={(e) => setPrescDetails(e.target.value)}
                  className="dashboard-textarea"
                  rows="3"
                ></textarea>
              </div>

              <button
                className="upload-btn"
                onClick={handlePrescriptionUpload}
                disabled={isUploading}
              >
                {isUploading ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-upload"></i>}
                {isUploading ? " Uploading..." : " Upload Prescription"}
              </button>
            </div>
          </div>
        </div>
      </main >

      <div id="open-ai-panel" onClick={() => setAiOpen(true)}>
        FlossyAI
      </div>

      <div className={`ai-panel ${aiOpen ? "open" : ""}`}>
        <div className="ai-header">
          🦷 FlossyAI Assistant
          <button className="close" onClick={() => setAiOpen(false)}>✖</button>
        </div>

        <div className="ai-content">
          {messages.map((m, i) => (
            <div key={i} className={m.from === "user" ? "msg-user" : "msg-ai"}>
              <b>{m.from === "user" ? "You" : "FlossyAI"}:</b> {m.text}
            </div>
          ))}
          {typing && <div className="typing">FlossyAI is typing<span className="dot-one">.</span><span className="dot-two">.</span><span className="dot-three">.</span></div>}
        </div>

        <div className="ai-input-area">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Ask FlossyAI..."
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
      </div>

      <Footer />

      {/* FOLLOW UP MODAL */}
      {
        followUpOpen && (
          <div className="modal-overlay" style={{
            position: "fixed", top: 0, left: 0, width: "100%", height: "100%",
            background: "rgba(0,0,0,0.8)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 10000
          }}>
            <div className="modal-content" style={{
              background: "#1a1a1a", padding: "2rem", borderRadius: "15px", width: "90%", maxWidth: "500px", border: "1px solid #333"
            }}>
              <h3 style={{ color: "#fff", marginBottom: "1rem" }}>Mark for Follow Up</h3>
              <p style={{ color: "#888", marginBottom: "1rem" }}>Why does this patient need to return?</p>
              <textarea
                value={followUpReason}
                onChange={e => setFollowUpReason(e.target.value)}
                placeholder="e.g. Needs gum checking in 2 weeks..."
                style={{ width: "100%", height: "100px", background: "#333", border: "none", color: "#fff", padding: "10px", borderRadius: "5px", marginBottom: "1rem" }}
              ></textarea>
              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                <button onClick={() => setFollowUpOpen(false)} style={{ padding: "10px 20px", background: "transparent", border: "1px solid #555", color: "#fff", borderRadius: "5px", cursor: "pointer" }}>Cancel</button>
                <button onClick={markFollowUp} style={{ padding: "10px 20px", background: "#f0b800", border: "none", color: "#000", borderRadius: "5px", cursor: "pointer", fontWeight: "bold" }}>Confirm Follow Up</button>
              </div>
            </div>
          </div>
        )
      }
    </>
  );
}
