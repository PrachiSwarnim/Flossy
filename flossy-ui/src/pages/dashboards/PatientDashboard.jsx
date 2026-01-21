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
  const [isTriageLoading, setIsTriageLoading] = useState(false);
  const [triageSymptom, setTriageSymptom] = useState("");
  const [triageResult, setTriageResult] = useState(null);
  const [profileVisible, setProfileVisible] = useState(true);
  const [isEditProfileOpen, setIsEditProfileOpen] = useState(false);
  const [editProfileData, setEditProfileData] = useState({
    name: "",
    phone: "",
    age: "",
    sex: "M"
  });

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

  // === Full Name ===
  const capitalizeFullName = (name) => {
    if (!name || typeof name !== 'string') return "";
    const localPart = name.split('@')[0];
    let parts = localPart.split(/[._-]/);
    const titles = ['mr', 'ms', 'mrs', 'dr', 'prof'];
    parts = parts.filter(part => !titles.includes(part.toLowerCase()));

    if (parts.length === 0) return "";

    if (parts.length >= 2) {
      return parts.map(part => {
        const cleanPart = part.replace(/\d+/g, "");
        return cleanPart.charAt(0).toUpperCase() + cleanPart.slice(1).toLowerCase();
      }).filter(p => p.length > 0).join(' ');
    }

    return parts.map(part => {
      const cleanPart = part.replace(/\d+/g, "");
      return cleanPart.charAt(0).toUpperCase() + cleanPart.slice(1).toLowerCase();
    }).filter(p => p.length > 0).join(' ');
  };

  const userEmail = user?.primaryEmailAddress?.emailAddress || "";
  const clerkName = user?.fullName || (user?.firstName ? `${user.firstName} ${user.lastName || ""}`.trim() : null);
  const fullName = clerkName || capitalizeFullName(userEmail) || "Patient";

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
    if (!isLoaded || !user) return;
    const role = user?.publicMetadata?.role || sessionStorage.getItem("flossy_role");
    const email = user?.primaryEmailAddress?.emailAddress?.toLowerCase();
    const isHardcodedDentist = ["prachi.swarnim@gmail.com", "choudhary.shruti01@gmail.com", "smileartistsdental@gmail.com"].includes(email);

    if (role === "dentist" || role === "receptionist" || isHardcodedDentist) {
      if (role === "dentist" || isHardcodedDentist) navigate("/dentist");
      else if (role === "receptionist") navigate("/receptionist");
    }
  }, [isLoaded, user, navigate]);

  // 1.5️⃣ LOAD AI SUGGESTION
  async function loadSuggestion() {
    if (!session) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/ai_suggestion`, {
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
      const res = await fetch(`${API}/api/patients/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setProfile(data);
        setEditProfileData({
          name: data.name || "",
          phone: (data.phone && data.phone.startsWith("TEMP_")) ? "" : (data.phone || ""),
          age: data.age || "",
          sex: data.sex || "Male" // Default to Male if not set
        });
      }
    } catch (e) {
      console.error("Profile load error", e);
    }
  }

  async function updateProfile() {
    if (!session) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/patients/me`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          ...editProfileData,
          age: editProfileData.age ? parseInt(editProfileData.age) : null
        })
      });
      if (res.ok) {
        setIsEditProfileOpen(false);
        loadProfile();
      } else {
        alert("Failed to update profile.");
      }
    } catch (err) {
      console.error("Update profile error", err);
    }
  }

  async function runTriage() {
    if (!triageSymptom.trim()) return;
    setIsTriageLoading(true);
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/ai/triage`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ symptoms: triageSymptom })
      });
      if (res.ok) {
        const data = await res.json();
        setTriageResult(data.triage);
        setTriageSymptom("");
      }
    } catch (err) {
      console.error("Triage error", err);
    } finally {
      setIsTriageLoading(false);
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
  async function sendMessage(customMsg = null) {
    const msg = customMsg || input;
    if (!msg || !msg.trim()) return;
    if (!session) return;

    if (!customMsg) setInput("");

    // INTERCEPT: If user asks to book a cleaning via chip
    if (msg === "Book a cleaning") {
      setMessages(prev => [...prev, { from: "user", text: msg }]);
      setTimeout(() => {
        setMessages(prev => [...prev, { from: "ai", text: `Sure thing, ${user.firstName || "there"}! Opening the booking form for you...` }]);
        setIsBookingOpen(true); // Open the modal
      }, 500);
      return;
    }

    setMessages((prev) => [...prev, { from: "user", text: msg }]);
    setTyping(true);

    try {
      const token = await session.getToken({ template: "default" });

      const aiRes = await fetch(`${API}/api/ai_response`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: msg,
          user_name: user.firstName || "there" // Pass user name to backend
        }),
      });

      if (!aiRes.ok) {
        throw new Error(`API returned ${aiRes.status}`);
      }

      const aiData = await aiRes.json();
      const answer = aiData.answer || `I'm here to help, ${user.firstName || "there"}! Could you rephrase that?`;

      setMessages((prev) => [...prev, { from: "ai", text: answer }]);
    } catch (error) {
      console.error("AI Response Error:", error);
      setMessages((prev) => [...prev, {
        from: "ai",
        text: `Sorry ${user.firstName || "there"}, I'm having trouble connecting. Please try again in a moment.`
      }]);
    } finally {
      setTyping(false);
      loadAppointments();
    }
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
    <div className={`dashboard-shell ${!profileVisible ? "sidebar-collapsed" : "sidebar-expanded"}`}>
      {/* PATIENT PROFILE SIDEBAR - Fixed to left */}
      <aside className="profile-sidebar">
        <div className="sidebar-expand-toggle" onClick={() => setProfileVisible(!profileVisible)}>
          <i className={`fas fa-chevron-${profileVisible ? 'left' : 'right'}`}></i>
        </div>

        <div className="profile-sidebar-content">
          <div className="profile-avatar">
            {user?.imageUrl ? (
              <img src={user.imageUrl} alt="Profile" />
            ) : (
              <div className="avatar-placeholder">
                <i className="fas fa-user"></i>
              </div>
            )}
          </div>

          <div className="profile-header-text">
            <h3 className="profile-name">
              {fullName}
            </h3>
            <span className="profile-role">Patient</span>
          </div>

          <div className="profile-info-grid">
            <div className="profile-stat">
              <span className="stat-value">{upcoming.length}</span>
              <span className="stat-label">Upcoming</span>
            </div>
            <div className="profile-stat">
              <span className="stat-value">{history.length}</span>
              <span className="stat-label">Past Visits</span>
            </div>
          </div>

          <div className="profile-details-compact">
            <div className="detail-row" title={profile?.email || user?.primaryEmailAddress?.emailAddress}>
              <i className="fas fa-envelope"></i>
              <span>{profile?.email || user?.primaryEmailAddress?.emailAddress || "No email"}</span>
            </div>
            <div className="detail-row">
              <i className="fas fa-phone"></i>
              <span>{(profile?.phone && !profile.phone.startsWith("TEMP_")) ? profile.phone : ""}</span>
            </div>
            <div className="detail-row">
              <i className="fas fa-birthday-cake"></i>
              <span>{profile?.age ? `${profile.age} years old` : ""}</span>
            </div>
            <div className="detail-row">
              <i className="fas fa-venus-mars"></i>
              <span>{profile?.sex || ""}</span>
            </div>

            <button className="edit-details-link" onClick={() => setIsEditProfileOpen(true)}>
              <i className="fas fa-pen"></i> Edit Personal Details
            </button>
          </div>

          <div className="sidebar-actions">
            <button className="edit-profile-btn" onClick={() => setIsEditProfileOpen(true)}>
              <i className="fas fa-edit"></i> <span>Edit Profile</span>
            </button>

            <button className="p-btn sidebar-book-btn" onClick={() => setIsBookingOpen(true)}>
              <i className="fas fa-calendar-plus"></i> <span>Book Appointment</span>
            </button>
          </div>
        </div>
      </aside>

      <div className="dashboard-main-content">
        <Header openAI={() => setAiOpen(true)} />

        <main className="patient-main">
          <h2 id="welcomeMessage">{isNewUser ? "Welcome" : "Welcome back"}, {fullName}!</h2>

          <div className="dashboard-content-grid">
            {/* MAIN CONTENT GRID */}
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

              {/* AI TRIAGE CARD (RECRUITER FLEX 💪) */}
              <div className="patient-card animate-fade-up" style={{ animationDelay: "0.25s", background: "linear-gradient(145deg, #1a1a1a, #2a2a2a)", border: "1px solid var(--primary-gold)" }}>
                <div className="card-header">
                  <h3 style={{ color: "var(--primary-gold)" }}>AI Dental Triage</h3>
                  <i className="fas fa-robot card-icon" style={{ color: "var(--primary-gold)" }}></i>
                </div>
                <div style={{ padding: '15px 0' }}>
                  <p style={{ fontSize: '0.85rem', color: '#ccc', marginBottom: '12px' }}>
                    Describe your pain or symptoms. Our AI will assess the urgency.
                  </p>
                  <textarea
                    className="triage-textarea"
                    placeholder="Describe your symptoms here (e.g. sharp pain, sensitivity...)"
                    value={triageSymptom}
                    onChange={(e) => setTriageSymptom(e.target.value)}
                  />
                  <button
                    className="p-btn"
                    onClick={runTriage}
                    disabled={isTriageLoading || !triageSymptom}
                    style={{ width: '100%', marginTop: '10px', opacity: (isTriageLoading || !triageSymptom) ? 0.6 : 1 }}
                  >
                    {isTriageLoading ? "Analyzing Symptoms..." : "Analyze Symptoms"}
                  </button>

                  {triageResult && (
                    <div className="triage-result animate-fade-in" style={{ marginTop: '20px', padding: '15px', borderRadius: '10px', background: 'rgba(212, 175, 55, 0.08)', border: '1px solid rgba(212, 175, 55, 0.2)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                        <div className={`urgency-badge ${triageResult.urgency}`} style={{
                          padding: '4px 10px',
                          borderRadius: '20px',
                          fontSize: '0.75rem',
                          fontWeight: 'bold',
                          textTransform: 'uppercase',
                          background: triageResult.urgency === 'emergency' ? '#ff3b30' : triageResult.urgency === 'soon' ? '#ffcc00' : '#4cd964',
                          color: triageResult.urgency === 'soon' ? '#000' : '#fff'
                        }}>
                          {triageResult.urgency}
                        </div>
                        <span style={{ fontWeight: 'bold', color: '#fff' }}>{triageResult.probable_issue}</span>
                      </div>
                      <p style={{ fontSize: '0.85rem', color: '#ddd', marginBottom: '8px' }}>
                        <i className="fas fa-microscope" style={{ marginRight: '5px', color: 'var(--primary-gold)' }}></i>
                        {triageResult.ai_reasoning}
                      </p>
                      <p style={{ fontSize: '0.85rem', color: 'var(--primary-gold)', fontWeight: '500' }}>
                        <i className="fas fa-hand-holding-medical" style={{ marginRight: '5px' }}></i>
                        {triageResult.patient_guidance}
                      </p>
                      <div style={{ marginTop: '12px', fontSize: '0.7rem', color: '#888', fontStyle: 'italic' }}>
                        * This is an AI assessment. Always consult a real dentist for medical advice.
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* AI INSIGHTS CARD */}
              <div className="patient-card animate-fade-up" style={{ animationDelay: "0.3s", gridColumn: "1 / -1" }}>
                <div className="card-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <h3>My Oral Health</h3>
                    <div className="info-tooltip-container">
                      <i className="fas fa-info-circle tooltip-trigger"></i>
                      <span className="tooltip-text">Updated by your dentist after clinical examinations.</span>
                    </div>
                  </div>
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
        {
          isRescheduleModalOpen && (
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
          )
        }

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
                  <button onClick={() => sendMessage("I have a toothache")}>🦷 Toothache</button>
                  <button onClick={() => sendMessage("Cost of dental implants")}>💰 Pricing</button>
                  <button onClick={() => sendMessage("Book a cleaning")}>📅 Book Cleaning</button>
                  <button onClick={() => sendMessage("Post-op care instructions")}>🩹 Post-op Care</button>
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

        {/* EDIT PROFILE MODAL */}
        {
          isEditProfileOpen && (
            <div className="modal-overlay" onClick={() => setIsEditProfileOpen(false)}>
              <div className="modal-content" style={{ maxWidth: '500px' }} onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                  <h3>Edit Your Profile</h3>
                  <button className="close-btn" onClick={() => setIsEditProfileOpen(false)}>&times;</button>
                </div>

                <div className="profile-edit-form">
                  <div className="form-group">
                    <label>Full Name</label>
                    <input
                      type="text"
                      value={editProfileData.name}
                      onChange={e => setEditProfileData({ ...editProfileData, name: e.target.value })}
                      placeholder="Your full name"
                    />
                  </div>

                  <div className="form-group">
                    <label>Phone Number</label>
                    <input
                      type="text"
                      value={editProfileData.phone}
                      onChange={e => setEditProfileData({ ...editProfileData, phone: e.target.value })}
                      placeholder="Contact number"
                    />
                  </div>

                  <div className="form-row-group">
                    <div className="form-group">
                      <label>Age</label>
                      <input
                        type="number"
                        value={editProfileData.age}
                        onChange={e => setEditProfileData({ ...editProfileData, age: e.target.value })}
                        placeholder="e.g. 25"
                      />
                    </div>
                    <div className="form-group">
                      <label>Sex</label>
                      <select
                        value={editProfileData.sex}
                        onChange={e => setEditProfileData({ ...editProfileData, sex: e.target.value })}
                      >
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>
                  </div>

                  <div className="modal-actions" style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                    <button className="p-btn small" onClick={() => setIsEditProfileOpen(false)} style={{ background: '#333' }}>Cancel</button>
                    <button className="p-btn small" onClick={updateProfile}>Save Changes</button>
                  </div>
                </div>
              </div>
            </div>
          )
        }
        <Footer />
      </div>
    </div>
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
