import { useEffect, useState } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { PropagateLoader } from "react-spinners";
import VoiceChat from "../../components/VoiceChat";
import Header from "./DashboardHeader";
import Footer from "../../components/Footer";
import InvoiceForm from "../../components/InvoiceForm";
import "../../styles/dentist_dashboard.css";
import "../../styles/dashboard_extras.css";

const API = "http://localhost:8000";

const DENTAL_MEDICATIONS = [
  // Antibiotics
  { name: "Amoxicillin 500mg", type: "Antibiotic" },
  { name: "Augmentin 625mg", type: "Antibiotic" },
  { name: "Metronidazole 400mg", type: "Antibiotic" },
  { name: "Clindamycin 300mg", type: "Antibiotic" },
  { name: "Azithromycin 500mg", type: "Antibiotic" },
  { name: "Oflox-OZ (Oflox + Ornidazole)", type: "Antibiotic" },
  { name: "Doxycycline 100mg", type: "Antibiotic" },

  // Pain Relief / NSAIDs
  { name: "Ibuprofen 400mg", type: "Pain Relief" },
  { name: "Ibuprofen 600mg", type: "Pain Relief" },
  { name: "Paracetamol 500mg", type: "Pain Relief" },
  { name: "Paracetamol 650mg", type: "Pain Relief" },
  { name: "Zerodol-P (Aceclofenac + PCM)", type: "Pain Relief" },
  { name: "Zerodol-SP (Aceclo + PCM + Serato)", type: "Pain Relief" },
  { name: "Ketorolac (Ketanov) 10mg", type: "Pain Relief" },
  { name: "Ketorol DT (Dr. Reddy's)", type: "Pain Relief" },
  { name: "Combiflam (Ibu + PCM)", type: "Pain Relief" },

  // Antacids (to be given with NSAIDs)
  { name: "Pantoprazole 40mg (Pan-40)", type: "Antacid" },
  { name: "Ranitidine 150mg (Rantac)", type: "Antacid" },
  { name: "Omeprazole 20mg", type: "Antacid" },

  // Steroids & Anti-inflammatory
  { name: "Dexamethasone 4mg", type: "Steroid" },
  { name: "Chymoral Forte", type: "Anti-inflammatory" },
  { name: "Prednisolone 5mg", type: "Steroid" },
  { name: "Wysolone 10mg", type: "Steroid" },

  // Mouthwashes & Topical
  { name: "Chlorhexidine Mouthwash", type: "Mouthwash" },
  { name: "Senquel AD Mouthwash", type: "Mouthwash" },
  { name: "Hexidine Mouthwash", type: "Mouthwash" },
  { name: "Lidocaine Topical Ointment", type: "Anesthetic" },
  { name: "Kenacort Oral Paste", type: "Topical Steroid" },
  { name: "Orasore Gel", type: "Ulcer Gel" },
  { name: "Candid Mouth Paint", type: "Antifungal" },
  { name: "Rexidin M Forte Gel", type: "Antiseptic Gel" },
  { name: "Omnigel (Topical Gel)", type: "Pain Relief" },

  // Hemostatics (Stop Bleeding)
  { name: "Tranexamic Acid 500mg (Pause)", type: "Hemostatic" },
  { name: "Ethamsylate 500mg (Revitostept)", type: "Hemostatic" },

  // Supplements & Specialized
  { name: "Vitamin C (Celin) 500mg", type: "Supplement" },
  { name: "Vitamin B-Complex (Becosules)", type: "Supplement" },
  { name: "Calcium + Vitamin D3 (Shelcal)", type: "Supplement" },
  { name: "Sensodyne Repair and Protect Toothpaste", type: "Toothpaste" },
  { name: "Thermoseal Toothpaste", type: "Toothpaste" },
  { name: "Vantej Toothpaste", type: "Toothpaste" },
];

export default function DentistDashboard() {
  const { user, isLoaded } = useUser();
  const { session } = useSession();
  const navigate = useNavigate();

  // 🔒 BLOCK ACCESS UNTIL LOADED
  useEffect(() => {
    if (!isLoaded) return;

    const role = user?.publicMetadata?.role;
    const email = user?.primaryEmailAddress?.emailAddress;

    // Allow Dentist OR Prachi specific bypass
    if (role !== "dentist" && email !== "prachi.swarnim@gmail.com") {
      navigate("/not-authorized");
    }
  }, [isLoaded, user, navigate]);

  // === Missing State (RESTORED) ===
  const [pageLoading, setPageLoading] = useState(true);
  const [today, setToday] = useState([]);
  const [upcoming, setUpcoming] = useState([]);
  const [history, setHistory] = useState([]);
  const [aiOpen, setAiOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);

  // Follow Up State
  const [followUpOpen, setFollowUpOpen] = useState(false);
  const [selectedApptId, setSelectedApptId] = useState(null);
  const [followUpReason, setFollowUpReason] = useState("");

  // VOICE AGENT (LiveKit Integrated)
  const [isVoiceActive, setIsVoiceActive] = useState(false);
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

  async function refreshAll() {
    console.log("🔄 AI Action detected: Refreshing Dentist Dashboard...");
    await loadAppointments();
    await loadHistoryPrescriptions();
  }


  // === Fetch Appointments ===
  async function loadAppointments() {
    const token = await session.getToken({ template: "default" });
    const res = await fetch(`${API}/api/appointments/dentist_upcoming`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    const data = await res.json();
    setToday(data.today || []);
    setUpcoming(data.upcoming || []);
    setHistory(data.history || []);
  }

  // === Load Data ===
  useEffect(() => {
    if (!isLoaded) return;

    // Check permission (Redundant with top-level check but safe)
    const role = user?.publicMetadata?.role;
    const email = user?.primaryEmailAddress?.emailAddress;

    if (role !== "dentist" && email !== "prachi.swarnim@gmail.com") return;

    // Start loading
    loadAppointments()
      .catch(e => console.error("Failed to load appointments:", e))
      .finally(() => setPageLoading(false));

    // Safety timeout: forced stop after 5 seconds
    const timer = setTimeout(() => setPageLoading(false), 5000);
    return () => clearTimeout(timer);
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

  async function markNotVisited(id) {
    if (!window.confirm("Mark this patient as 'Not Visited'?")) return;
    const token = await session.getToken({ template: "default" });
    await fetch(`${API}/api/appointments/mark_completed/${id}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ status: "missed" })
    });
    loadAppointments();
  }

  async function updateFollowUpStatus(apptId, status) {
    const token = await session.getToken({ template: "default" });
    try {
      const res = await fetch(`${API}/api/appointments/${apptId}/follow_up_status`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ status })
      });
      if (res.ok) {
        loadAppointments();
      } else {
        alert("Failed to update follow-up status.");
      }
    } catch (err) {
      console.error("Error updating follow-up status:", err);
    }
  }

  function capitalizeFullName(name) {
    if (!name) return "";
    return name
      .trim()
      .split(/\s+/)
      .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(" ");
  }

  function addMedication(medName) {
    if (!medName) return;
    setPrescRecommendations(prev => {
      const newLine = prev && !prev.endsWith("\n") ? "\n• " : (prev ? "• " : "• ");
      return prev + newLine + medName;
    });
  }


  // === Prescription State ===
  const [prescPatient, setPrescPatient] = useState("");
  const [editingPrescId, setEditingPrescId] = useState(null);
  const [prescDate, setPrescDate] = useState(new Date().toISOString().split('T')[0]);
  const [prescDetails, setPrescDetails] = useState("");
  const [prescDiagnosis, setPrescDiagnosis] = useState("");
  const [prescTreatment, setPrescTreatment] = useState("");
  const [prescRecommendations, setPrescRecommendations] = useState("");
  const [medSearch, setMedSearch] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [patientSearch, setPatientSearch] = useState("");
  const [showPatientSuggestions, setShowPatientSuggestions] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [patientsList, setPatientsList] = useState([]);
  const [historyPrescriptions, setHistoryPrescriptions] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [editingInvoice, setEditingInvoice] = useState(null);

  async function startEditingInvoice(inv) {
    if (!inv || !inv.id) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/invoices/${inv.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setEditingInvoice(data);
        // Scroll to form
        document.querySelector('.row-billing')?.scrollIntoView({ behavior: 'smooth' });
      } else {
        alert("Failed to load invoice details.");
      }
    } catch (e) {
      console.error("Error loading invoice:", e);
      alert("Error loading invoice.");
    }
  }

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
        } else {
          console.error("Patients Fetch Error:", res.status);
          alert(`Failed to load patient list (Error ${res.status}). Please check console.`);
        }
      } catch (err) {
        console.error("Failed to load patients", err);
      }
    }

    fetchPatients();
    loadHistoryPrescriptions();
    fetchInvoices();
    migrateLegacyPrescriptions();
  }, [isLoaded, session]);

  async function fetchInvoices() {
    if (!session) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/invoices/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setInvoices(data.invoices);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function downloadInvoice(id, invNum, stamp = true, patientName = "") {
    if (!session) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/invoices/${id}/pdf?stamp=${stamp}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const safeName = patientName ? patientName.replace(/[^a-zA-Z0-9]/g, "_") : "";
        a.download = `${safeName}_invoice_${invNum}${stamp ? "" : "_plain"}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function migrateLegacyPrescriptions() {
    if (!session) return;
    const legacy = localStorage.getItem("flossy_prescriptions");
    if (!legacy) return;

    try {
      const prescList = JSON.parse(legacy);
      if (!Array.isArray(prescList) || prescList.length === 0) {
        localStorage.removeItem("flossy_prescriptions");
        return;
      }

      console.log("🛠️ Migrating legacy prescriptions to backend...");
      const token = await session.getToken({ template: "default" });

      for (const p of prescList) {
        // We only migrate if we have a patient name and details
        if (!p.patient || !p.details) continue;

        await fetch(`${API}/api/prescriptions`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            patient_name: p.patient,
            details: p.details
          })
        });
      }

      localStorage.removeItem("flossy_prescriptions");
      console.log("✅ Migration complete.");
      loadHistoryPrescriptions();
    } catch (err) {
      console.error("Migration failed", err);
    }
  }

  async function loadHistoryPrescriptions() {
    if (!session) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/prescriptions/dentist`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setHistoryPrescriptions(data.prescriptions || []);
      }
    } catch (err) {
      console.error("Failed to load prescription history", err);
    }
  }

  async function downloadPrescription(id, stamp = true, patientName = "") {
    if (!session) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/prescriptions/${id}/pdf?stamp=${stamp}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const safeName = patientName ? patientName.replace(/[^a-zA-Z0-9]/g, "_") : "";
        a.download = `${safeName}_prescription${stamp ? "" : "_plain"}.pdf`;
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

  // === Prescription Handling ===
  const handleBulletInput = (e, setter, currentVal) => {
    const bullet = "• ";
    // If it's the first character being typed, add a bullet
    if (e.target.value.length === 1 && !currentVal) {
      setter(bullet + e.target.value);
      return;
    }

    // Handle Enter key for new bullets
    if (e.nativeEvent.inputType === "insertLineBreak") {
      setter(currentVal + "\n" + bullet);
      return;
    }

    setter(e.target.value);
    setter(e.target.value);
  };

  function startEditing(p) {
    setEditingPrescId(p.id);
    setPrescPatient(p.patient);
    setPatientSearch(p.patient);
    setPrescDate(p.date ? p.date.split('T')[0] : new Date().toISOString().split('T')[0]);
    setPrescDetails(p.details || "");
    setPrescDiagnosis(p.diagnosis || "");
    setPrescTreatment(p.treatment_plan || "");
    setPrescRecommendations(p.recommendations || "");
    // Scroll to form
    document.querySelector('.prescription-form')?.scrollIntoView({ behavior: 'smooth' });
  }

  function cancelEditing() {
    setEditingPrescId(null);
    setPrescPatient("");
    setPatientSearch("");
    setPrescDetails("");
    setPrescDiagnosis("");
    setPrescTreatment("");
    setPrescRecommendations("");
    setPrescDate(new Date().toISOString().split('T')[0]);
  }

  async function handlePrescriptionUpload() {
    if (!prescPatient) return alert("Select a patient first.");
    if (!prescDiagnosis && !prescTreatment && !prescRecommendations && !prescDetails)
      return alert("Please fill at least one prescription section.");

    setIsUploading(true);

    try {
      const token = await session.getToken({ template: "default" });
      const url = editingPrescId
        ? `${API}/api/prescriptions/${editingPrescId}`
        : `${API}/api/prescriptions`;

      const method = editingPrescId ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          patient_name: prescPatient,
          details: prescDetails,
          diagnosis: prescDiagnosis,
          treatment_plan: prescTreatment,
          recommendations: prescRecommendations,
          created_at: prescDate
        })
      });

      if (res.ok) {
        setPrescPatient("");
        setPatientSearch("");
        setPrescDetails("");
        setPrescDiagnosis("");
        setPrescTreatment("");
        setPrescRecommendations("");
        setEditingPrescId(null); // Reset edit mode

        alert(`Prescription ${editingPrescId ? "updated" : "uploaded"} successfully!`);
        loadHistoryPrescriptions();
      } else {
        const err = await res.json();
        alert((editingPrescId ? "Update" : "Upload") + " failed: " + (err.detail || "Unknown error"));
      }
    } catch (err) {
      console.error("Prescription upload error:", err);
      alert("System error during upload.");
    } finally {
      setIsUploading(false);
    }
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
        <h2 id="Message">Welcome back, Dr. {fullName}!</h2>

        <div className="dashboard-layout" style={{ display: "flex", flexDirection: "column", gap: "2rem", paddingBottom: "3rem" }}>

          {/* ROW 1: APPOINTMENTS (SIDE BY SIDE) */}
          <div className="row-appointments" style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "1.5rem" }}>

            {/* TODAY */}
            <div className="card animate-fade-up" style={{ animationDelay: "0.1s", flex: "1", minWidth: "400px", maxWidth: "600px" }}>
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
                    <div className="appt-patient">{capitalizeFullName(a.patient_name)}
                      <span style={{ marginLeft: "10px", fontSize: "0.85rem", opacity: 0.7 }}>
                        {a.patient_age && `(Age: ${a.patient_age})`} {a.patient_phone && ` • 📞 ${a.patient_phone}`}
                      </span>
                    </div>
                    <div className="appt-reason">{a.reason}</div>

                    {/* 🔥 Buttons */}
                    {a.status === "scheduled" && (
                      <div className="action-buttons" style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                        <button
                          className="done-btn"
                          onClick={() => markCompleted(a.id)}
                          style={{ height: "40px", padding: "0 12px", background: "#2ecc71", color: "#fff", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold", flex: 1, display: "flex", alignItems: "center", justifyContent: "center", whiteSpace: "nowrap" }}
                        >
                          <i className="fas fa-check" style={{ marginRight: "8px" }}></i> Completed
                        </button>
                        <button
                          className="follow-up-btn"
                          style={{ height: "40px", padding: "0 12px", background: "#f0b800", color: "#000", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold", flex: 1, display: "flex", alignItems: "center", justifyContent: "center", whiteSpace: "nowrap" }}
                          onClick={() => openFollowUpModal(a.id)}
                        >
                          <i className="fas fa-clock" style={{ marginRight: "8px" }}></i> Follow Up
                        </button>
                        <button
                          className="missed-btn"
                          style={{ height: "40px", padding: "0 12px", background: "#e74c3c", color: "#fff", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold", flex: 1, display: "flex", alignItems: "center", justifyContent: "center", whiteSpace: "nowrap" }}
                          onClick={() => markNotVisited(a.id)}
                        >
                          <i className="fas fa-times" style={{ marginRight: "8px" }}></i> Not Visited
                        </button>
                      </div>
                    )}

                    {a.status === "completed" && (
                      <span className="completed-tag" style={{ color: "#2ecc71", display: "block", marginTop: "5px" }}>
                        <i className="fas fa-check-circle"></i> Completed
                      </span>
                    )}

                    {a.status === "missed" && (
                      <span className="missed-tag" style={{ color: "#e74c3c", display: "block", marginTop: "5px" }}>
                        <i className="fas fa-times-circle"></i> Not Visited
                      </span>
                    )}

                    {a.status === "follow_up" && (
                      <div className="follow-up-tag" style={{ color: "#f0b800", marginTop: "5px" }}>
                        <i className="fas fa-clock"></i> Follow Up Required
                        <div style={{ fontSize: "0.8rem", opacity: 0.8 }}>Note: {a.follow_up_reason}</div>

                        {/* Follow-up Status Tracking */}
                        <div className="follow-up-actions" style={{ marginTop: "8px", display: "flex", gap: "8px" }}>
                          {!a.follow_up_status ? (
                            <>
                              <button
                                onClick={() => updateFollowUpStatus(a.id, "completed")}
                                style={{ fontSize: "0.75rem", background: "#28a745", color: "#fff", border: "none", padding: "4px 8px", borderRadius: "4px", cursor: "pointer" }}
                              >Mark Done</button>
                              <button
                                onClick={() => updateFollowUpStatus(a.id, "missed")}
                                style={{ fontSize: "0.75rem", background: "#dc3545", color: "#fff", border: "none", padding: "4px 8px", borderRadius: "4px", cursor: "pointer" }}
                              >Mark Missed</button>
                            </>
                          ) : (
                            <span style={{
                              fontSize: "0.75rem",
                              fontWeight: "bold",
                              color: a.follow_up_status === "completed" ? "#28a745" : "#dc3545",
                              textTransform: "capitalize"
                            }}>
                              Follow-up {a.follow_up_status}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <p className="empty-state">No appointments remaining today.</p>
              )}
            </div>

            {/* UPCOMING */}
            <div className="card animate-fade-up" style={{ animationDelay: "0.15s", flex: "1", minWidth: "400px", maxWidth: "600px" }}>
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
                    <div className="appt-patient">{capitalizeFullName(a.patient_name)}
                      <span style={{ marginLeft: "10px", fontSize: "0.85rem", opacity: 0.7 }}>
                        {a.patient_age && `(Age: ${a.patient_age})`} {a.patient_phone && ` • 📞 ${a.patient_phone}`}
                      </span>
                    </div>
                    <div className="appt-reason">{a.reason}</div>
                    <div className="appt-status status-upcoming">Scheduled</div>
                  </div>
                ))
              ) : (
                <p className="empty-state">No upcoming appointments.</p>
              )}
            </div>

          </div>

          {/* ROW 1.5: HISTORY (CENTERED) */}
          <div className="row-history" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
            <div className="card animate-fade-up" style={{ animationDelay: "0.2s", width: "100%", maxWidth: "1000px" }}>
              <div className="card-header">
                <h3>Appointment History</h3>
                <i className="fas fa-history card-icon"></i>
              </div>
              <div className="history-list">
                {history.length ? (
                  history.map((a) => (
                    <div className="appt-item" key={a.id} style={{ opacity: (!a.status || !["completed", "missed", "follow_up"].includes(a.status)) ? 1 : 0.7 }}>
                      <b>
                        {new Date(a.time).toLocaleDateString()} {new Date(a.time).toLocaleTimeString("en-IN", {
                          hour: "2-digit",
                          minute: "2-digit",
                          hour12: true
                        })}
                      </b>
                      <div className="appt-patient">{capitalizeFullName(a.patient_name)}
                        <span style={{ marginLeft: "10px", fontSize: "0.85rem", opacity: 0.7 }}>
                          {a.patient_age && `(Age: ${a.patient_age})`} {a.patient_phone && ` • 📞 ${a.patient_phone}`}
                        </span>
                      </div>
                      <div className="appt-reason">{a.reason}</div>

                      {/* Overdue/Past Scheduled items still actionable */}
                      {(!a.status || !["completed", "missed", "follow_up"].includes(a.status)) && (
                        <>
                          <span style={{ color: "#e74c3c", fontWeight: "bold", display: "block", marginTop: "5px", marginBottom: "5px" }}>
                            ⚠️ Overdue / Past Pending
                          </span>
                          <div className="action-buttons" style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                            <button
                              className="done-btn"
                              onClick={() => markCompleted(a.id)}
                              style={{ height: "40px", padding: "0 12px", background: "#2ecc71", color: "#fff", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold", flex: 1, display: "flex", alignItems: "center", justifyContent: "center", whiteSpace: "nowrap" }}
                            >
                              <i className="fas fa-check" style={{ marginRight: "8px" }}></i> Completed
                            </button>
                            <button
                              className="follow-up-btn"
                              style={{ height: "40px", padding: "0 12px", background: "#f0b800", color: "#000", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold", flex: 1, display: "flex", alignItems: "center", justifyContent: "center", whiteSpace: "nowrap" }}
                              onClick={() => openFollowUpModal(a.id)}
                            >
                              <i className="fas fa-clock" style={{ marginRight: "8px" }}></i> Follow Up
                            </button>
                            <button
                              className="missed-btn"
                              style={{ height: "40px", padding: "0 12px", background: "#e74c3c", color: "#fff", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold", flex: 1, display: "flex", alignItems: "center", justifyContent: "center", whiteSpace: "nowrap" }}
                              onClick={() => markNotVisited(a.id)}
                            >
                              <i className="fas fa-times" style={{ marginRight: "8px" }}></i> Not Visited
                            </button>
                          </div>
                        </>
                      )}

                      {a.status === "completed" && (
                        <span className="completed-tag" style={{ color: "#2ecc71", display: "block", marginTop: "5px" }}>
                          <i className="fas fa-check-circle"></i> Completed
                        </span>
                      )}

                      {a.status === "missed" && (
                        <span className="missed-tag" style={{ color: "#e74c3c", display: "block", marginTop: "5px" }}>
                          <i className="fas fa-times-circle"></i> Not Visited
                        </span>
                      )}

                      {a.status === "follow_up" && (
                        <div className="follow-up-tag" style={{ color: "#f0b800", marginTop: "5px" }}>
                          <i className="fas fa-clock"></i> Follow Up Required
                          <div style={{ fontSize: "0.8rem", opacity: 0.8 }}>Note: {a.follow_up_reason}</div>
                          {/* History Follow-ups can still be acted upon */}
                          <div className="follow-up-actions" style={{ marginTop: "8px", display: "flex", gap: "8px" }}>
                            {!a.follow_up_status ? (
                              <>
                                <button
                                  onClick={() => updateFollowUpStatus(a.id, "completed")}
                                  style={{ fontSize: "0.75rem", background: "#28a745", color: "#fff", border: "none", padding: "4px 8px", borderRadius: "4px", cursor: "pointer" }}
                                >Mark Done</button>
                                <button
                                  onClick={() => updateFollowUpStatus(a.id, "missed")}
                                  style={{ fontSize: "0.75rem", background: "#dc3545", color: "#fff", border: "none", padding: "4px 8px", borderRadius: "4px", cursor: "pointer" }}
                                >Mark Missed</button>
                              </>
                            ) : (
                              <span style={{
                                fontSize: "0.75rem",
                                fontWeight: "bold",
                                color: a.follow_up_status === "completed" ? "#28a745" : "#dc3545",
                                textTransform: "capitalize"
                              }}>
                                Follow-up {a.follow_up_status}
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="empty-state">No appointment history found.</p>
                )}
              </div>
            </div>
          </div>

          {/* ROW 2: PRESCRIPTIONS (CENTERED) */}
          <div className="row-prescriptions" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
            <div className="card animate-fade-up" style={{ animationDelay: "0.2s", width: "100%", maxWidth: "1000px" }}>
              <div className="card-header">
                <h3>Prescriptions</h3>
                <i className="fas fa-file-prescription card-icon"></i>
              </div>
              <div className="prescription-form">
                <div style={{ display: "flex", gap: "1rem" }}>
                  <div className="form-group" style={{ position: "relative", flex: 1 }}>
                    <label>Select Patient</label>
                    <div className="patient-search-container" style={{ position: "relative" }}>
                      <div style={{ position: "relative" }}>
                        <input
                          type="text"
                          placeholder="Search patient name..."
                          value={patientSearch || prescPatient}
                          onChange={(e) => {
                            setPatientSearch(e.target.value);
                            setShowPatientSuggestions(true);
                            if (prescPatient) setPrescPatient(""); // Clear selection if typing
                          }}
                          onFocus={() => setShowPatientSuggestions(true)}
                          className="dashboard-input"
                          style={{ paddingLeft: "35px" }}
                        />
                        <i className="fas fa-search" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "#f0b800", opacity: 0.7 }}></i>
                        {(patientSearch || prescPatient) && (
                          <i
                            className="fas fa-times-circle"
                            style={{ position: "absolute", right: "12px", top: "50%", transform: "translateY(-50%)", color: "#888", cursor: "pointer" }}
                            onClick={() => {
                              setPatientSearch("");
                              setPrescPatient("");
                            }}
                          ></i>
                        )}
                      </div>

                      {showPatientSuggestions && (patientSearch.trim() !== "" || patientsList.length > 0) && (
                        <div className="patient-suggestions elegant-scroll" style={{
                          position: "absolute", top: "100%", left: 0, right: 0,
                          zIndex: 101, background: "#1a1a1a", border: "1px solid #444",
                          borderRadius: "8px", marginTop: "5px", maxHeight: "180px",
                          overflowY: "scroll", boxShadow: "0 10px 25px rgba(0,0,0,0.5)"
                        }}>
                          {patientsList
                            .filter(p => p.name.toLowerCase().includes(patientSearch.toLowerCase()))
                            .map((p, i) => (
                              <div
                                key={p.id}
                                onClick={() => {
                                  setPrescPatient(p.name);
                                  setPatientSearch(p.name);
                                  setShowPatientSuggestions(false);
                                }}
                                style={{
                                  padding: "10px 15px", cursor: "pointer", borderBottom: "1px solid #333",
                                  background: prescPatient === p.name ? "#2a2a2a" : "transparent"
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.background = "#2a2a2a"}
                                onMouseLeave={(e) => e.currentTarget.style.background = prescPatient === p.name ? "#2a2a2a" : "transparent"}
                              >
                                <div style={{ fontWeight: "600", color: "#fff" }}>{p.name}</div>
                                {p.phone && <div style={{ fontSize: "0.75rem", color: "#888" }}>{p.phone}</div>}
                              </div>
                            ))}
                          {patientsList.filter(p => p.name.toLowerCase().includes(patientSearch.toLowerCase())).length === 0 && (
                            <div style={{ padding: "15px", color: "#888", textAlign: "center" }}>No patients found.</div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Close suggestions when clicking outside */}
                    {showPatientSuggestions && (
                      <div
                        style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 100 }}
                        onClick={() => setShowPatientSuggestions(false)}
                      ></div>
                    )}
                  </div>
                  <div className="form-group" style={{ width: "180px" }}>
                    <label>Date</label>
                    <input type="date" value={prescDate} onChange={e => setPrescDate(e.target.value)} className="dashboard-input" />
                  </div>
                </div>

                <div className="form-group" style={{ marginBottom: "1rem" }}>
                  <label>Chief Complaint</label>
                  <textarea
                    placeholder="e.g. Severe toothache..."
                    value={prescDetails}
                    onChange={e => setPrescDetails(e.target.value)}
                    className="dashboard-textarea"
                    rows="2"
                  ></textarea>
                </div>

                <div className="structured-presc-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                  <div className="form-group">
                    <label>Diagnosis</label>
                    <textarea
                      placeholder="e.g. Chronic Gingivitis..."
                      value={prescDiagnosis}
                      onChange={(e) => handleBulletInput(e, setPrescDiagnosis, prescDiagnosis)}
                      className="dashboard-textarea"
                      rows="3"
                    ></textarea>
                  </div>

                  <div className="form-group">
                    <label>Treatment Plan</label>
                    <textarea
                      placeholder="e.g. Scaling and Root Planing..."
                      value={prescTreatment}
                      onChange={(e) => handleBulletInput(e, setPrescTreatment, prescTreatment)}
                      className="dashboard-textarea"
                      rows="3"
                    ></textarea>
                  </div>

                  <div className="form-group" style={{ gridColumn: "span 2", position: "relative" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <label style={{ margin: 0 }}>Recommendations / Medications</label>

                      {/* Search Bar for Medications */}
                      <div className="med-search-container" style={{ position: "relative", width: "100%", maxWidth: "350px" }}>
                        <div style={{ position: "relative" }}>
                          <input
                            type="text"
                            placeholder="Search medications..."
                            value={medSearch}
                            onChange={(e) => {
                              setMedSearch(e.target.value);
                              setShowSuggestions(true);
                            }}
                            onFocus={() => setShowSuggestions(true)}
                            className="dashboard-input"
                            style={{
                              padding: "8px 12px 8px 35px",
                              height: "38px",
                              fontSize: "0.9rem",
                              borderRadius: "8px",
                              border: "1px solid #444",
                              background: "#222"
                            }}
                          />
                          <i className="fas fa-search" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "#f0b800", opacity: 0.7 }}></i>
                        </div>

                        {showSuggestions && medSearch.trim() !== "" && (
                          <div className="med-suggestions elegant-scroll" style={{
                            position: "absolute", top: "100%", left: 0, right: 0,
                            zIndex: 100, background: "#1a1a1a", border: "1px solid #444",
                            borderRadius: "8px", marginTop: "5px", maxHeight: "250px",
                            overflowY: "scroll", boxShadow: "0 10px 25px rgba(0,0,0,0.5)"
                          }}>
                            {DENTAL_MEDICATIONS.filter(m =>
                              m.name.toLowerCase().includes(medSearch.toLowerCase()) ||
                              m.type.toLowerCase().includes(medSearch.toLowerCase())
                            ).map((m, i) => (
                              <div
                                key={i}
                                onClick={() => {
                                  addMedication(m.name);
                                  setMedSearch("");
                                  setShowSuggestions(false);
                                }}
                                style={{
                                  padding: "10px 15px", cursor: "pointer", borderBottom: "1px solid #333",
                                  transition: "background 0.2s"
                                }}
                                onMouseEnter={(e) => e.target.style.background = "#2a2a2a"}
                                onMouseLeave={(e) => e.target.style.background = "transparent"}
                              >
                                <div style={{ fontWeight: "bold", color: "#fff" }}>{m.name}</div>
                                <div style={{ fontSize: "0.75rem", color: "#f0b800" }}>{m.type}</div>
                              </div>
                            ))}
                            {DENTAL_MEDICATIONS.filter(m =>
                              m.name.toLowerCase().includes(medSearch.toLowerCase()) ||
                              m.type.toLowerCase().includes(medSearch.toLowerCase())
                            ).length === 0 && (
                                <div style={{ padding: "15px", color: "#888", textAlign: "center" }}>No medications found.</div>
                              )}
                          </div>
                        )}
                      </div>
                    </div>
                    <textarea
                      placeholder="e.g. Warm salt water rinses, twice daily..."
                      value={prescRecommendations}
                      onChange={(e) => handleBulletInput(e, setPrescRecommendations, prescRecommendations)}
                      className="dashboard-textarea"
                      rows="4"
                    ></textarea>

                    {/* Close suggestions when clicking outside */}
                    {showSuggestions && (
                      <div
                        style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 90 }}
                        onClick={() => setShowSuggestions(false)}
                      ></div>
                    )}
                  </div>
                </div>

                <button
                  className="upload-btn"
                  onClick={handlePrescriptionUpload}
                  disabled={isUploading}
                  style={{ marginTop: "1rem", background: editingPrescId ? "#2ecc71" : "#f0b800", color: editingPrescId ? "#fff" : "#000" }}
                >
                  {isUploading ? <i className="fas fa-spinner fa-spin"></i> : <i className={`fas ${editingPrescId ? "fa-save" : "fa-upload"}`}></i>}
                  {isUploading ? (editingPrescId ? " Updating..." : " Uploading...") : (editingPrescId ? " Update Prescription" : " Upload Prescription")}
                </button>
                {editingPrescId && (
                  <button
                    onClick={cancelEditing}
                    style={{ marginLeft: "10px", background: "transparent", border: "1px solid #777", color: "#ccc", padding: "10px 20px", borderRadius: "8px", cursor: "pointer" }}
                  >
                    Cancel Edit
                  </button>
                )}
              </div>


              {/* PREVIOUS PRESCRIPTIONS LIST */}
              {historyPrescriptions.length > 0 && prescPatient && (
                <div className="recent-prescriptions" style={{ marginTop: "2rem", borderTop: "1px solid #333", paddingTop: "1rem" }}>
                  <h4 style={{ marginBottom: "1rem", color: "#f0b800" }}>
                    {prescPatient ? `Prescriptions for ${prescPatient}` : "Recent Prescriptions"}
                  </h4>
                  <div className="presc-list" style={{ maxHeight: "300px", overflowY: "auto" }}>
                    {historyPrescriptions
                      .filter(p => !prescPatient || p.patient.toLowerCase() === prescPatient.toLowerCase())
                      .map(p => (
                        <div key={p.id} className="presc-item-mini" style={{
                          background: "#222", padding: "10px", borderRadius: "8px", marginBottom: "10px",
                          display: "flex", justifyContent: "space-between", alignItems: "center"
                        }}>
                          <div>
                            <b style={{ color: "#fff" }}>{capitalizeFullName(p.patient)}</b>
                            <div style={{ fontSize: "0.8rem", color: "#888" }}>{new Date(p.date).toLocaleDateString()}</div>
                            <div style={{ fontSize: "0.85rem", color: "#ccc", marginTop: "4px" }}>
                              {p.diagnosis ? `Dx: ${p.diagnosis.substring(0, 40)}...` :
                                p.details ? p.details.substring(0, 40) + "..." : "No details"}
                            </div>
                          </div>
                          <div style={{ display: "flex", gap: "8px" }}>
                            <button
                              onClick={() => startEditing(p)}
                              style={{ background: "#222", border: "1px solid #555", color: "#f0b800", padding: "5px 10px", borderRadius: "4px", fontSize: "0.8rem", cursor: "pointer" }}
                            >
                              <i className="fas fa-edit"></i> Edit
                            </button>
                            <button
                              onClick={() => downloadPrescription(p.id, true, p.patient)}
                              style={{ background: "#f0b800", border: "none", color: "#000", padding: "5px 10px", borderRadius: "4px", fontSize: "0.8rem", cursor: "pointer", fontWeight: "bold" }}
                            >
                              <i className="fas fa-stamp"></i> Stamped
                            </button>
                            <button
                              onClick={() => downloadPrescription(p.id, false, p.patient)}
                              style={{ background: "transparent", border: "1px solid #555", color: "#888", padding: "5px 10px", borderRadius: "4px", fontSize: "0.8rem", cursor: "pointer" }}
                            >
                              Plain
                            </button>
                          </div>
                        </div>
                      ))}
                    {prescPatient && historyPrescriptions.filter(p => p.patient.toLowerCase() === prescPatient.toLowerCase()).length === 0 && (
                      <p style={{ color: "#888", fontStyle: "italic" }}>No prescriptions found for this patient.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ROW 3: BILLING & INVOICES (CENTERED) */}
          <div className="row-billing" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
            <div className="card animate-fade-up" style={{ animationDelay: "0.3s", width: "100%", maxWidth: "1000px" }}>
              <div className="card-header">
                <h3>Billing & Invoices</h3>
                <i className="fas fa-file-invoice-dollar card-icon"></i>
              </div>
              <InvoiceForm
                patientsList={patientsList}
                onInvoiceCreated={() => { fetchInvoices(); setEditingInvoice(null); }}
                downloadInvoice={downloadInvoice}
                editingInvoice={editingInvoice}
                onCancelEdit={() => setEditingInvoice(null)}
                preSelectedPatient={prescPatient}
              />


              {invoices.length > 0 && prescPatient && (
                <div className="recent-prescriptions" style={{ marginTop: "2rem", borderTop: "1px solid #333", paddingTop: "1rem" }}>
                  <h4 style={{ marginBottom: "1rem", color: "#f0b800" }}>
                    {prescPatient ? `Invoices for ${prescPatient}` : "Recent Invoices"}
                  </h4>
                  <div className="presc-list elegant-scroll" style={{ maxHeight: "300px", overflowY: "auto" }}>
                    {invoices
                      .filter(inv => !prescPatient || (inv.patient_name || "").toLowerCase() === prescPatient.toLowerCase())
                      .map(inv => (
                        <div key={inv.id} className="presc-item-mini" style={{
                          background: "#222", padding: "10px", borderRadius: "8px", marginBottom: "10px",
                          display: "flex", justifyContent: "space-between", alignItems: "center"
                        }}>
                          <div>
                            <b style={{ color: "#fff" }}>{inv.patient_name}</b>
                            <div style={{ fontSize: "0.8rem", color: "#888" }}>{new Date(inv.date).toLocaleDateString()}</div>
                            <div style={{ fontSize: "0.85rem", color: "#2ecc71" }}>{inv.currency} {inv.total.toLocaleString()} ({inv.invoice_number})</div>
                          </div>
                          <div style={{ display: "flex", gap: "8px" }}>
                            <button
                              onClick={() => startEditingInvoice(inv)}
                              style={{ background: "#2ecc71", border: "none", color: "#000", padding: "5px 10px", borderRadius: "4px", fontSize: "0.8rem", cursor: "pointer", fontWeight: "bold" }}
                            >
                              <i className="fas fa-edit"></i> Edit
                            </button>
                            <button
                              onClick={() => downloadInvoice(inv.id, inv.invoice_number, true, inv.patient_name)}
                              style={{ background: "#f0b800", border: "none", color: "#000", padding: "5px 10px", borderRadius: "4px", fontSize: "0.8rem", cursor: "pointer", fontWeight: "bold" }}
                            >
                              <i className="fas fa-stamp"></i> Stamped
                            </button>
                            <button
                              onClick={() => downloadInvoice(inv.id, inv.invoice_number, false, inv.patient_name)}
                              style={{ background: "transparent", border: "1px solid #555", color: "#888", padding: "5px 10px", borderRadius: "4px", fontSize: "0.8rem", cursor: "pointer" }}
                            >
                              Plain
                            </button>
                          </div>
                        </div>
                      ))}
                    {prescPatient && invoices.filter(inv => (inv.patient_name || "").toLowerCase() === prescPatient.toLowerCase()).length === 0 && (
                      <p style={{ color: "#888", fontStyle: "italic" }}>No invoices found for this patient.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ROW 4: ALL REGISTERED PATIENTS (CENTERED) */}
          <div className="row-patients" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
            <div className="card animate-fade-up" style={{ animationDelay: "0.4s", width: "100%", maxWidth: "1000px" }}>
              <div className="card-header">
                <h3>All Registered Patients</h3>
                <i className="fas fa-users card-icon"></i>
              </div>
              <div className="elegant-scroll" style={{ padding: "1rem", overflowX: "auto", maxHeight: "300px", overflowY: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", color: "#fff", textAlign: "left" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid #333" }}>
                      <th style={{ padding: "12px", color: "#f0b800" }}>Name</th>
                      <th style={{ padding: "12px", color: "#f0b800" }}>Phone</th>
                      <th style={{ padding: "12px", color: "#f0b800" }}>Email</th>
                      <th style={{ padding: "12px", color: "#f0b800" }}>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {patientsList.length > 0 ? (
                      patientsList.map(p => (
                        <tr key={p.id} style={{ borderBottom: "1px solid #222" }}>
                          <td style={{ padding: "12px" }}>{p.name}</td>
                          <td style={{ padding: "12px", color: "#888" }}>{p.phone}</td>
                          <td style={{ padding: "12px", color: "#888" }}>{p.email || "-"}</td>
                          <td style={{ padding: "12px" }}>
                            <span style={{
                              padding: "4px 8px",
                              borderRadius: "4px",
                              fontSize: "0.75rem",
                              background: p.source === "website" ? "#3498db33" : p.source === "manual" ? "#e67e2233" : "#9b59b633",
                              color: p.source === "website" ? "#3498db" : p.source === "manual" ? "#e67e22" : "#9b59b6",
                              textTransform: "uppercase",
                              fontWeight: "bold"
                            }}>
                              {p.source || "website"}
                            </span>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="4" style={{ textAlign: "center", padding: "2rem", color: "#888" }}>No patients found.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

        </div>
      </main>

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
            onClick={() => setIsVoiceActive(true)}
            title="Start Clinical Voice Assistant"
            style={{ background: "#ffcb05", borderRadius: "50%", width: "40px", height: "40px", border: "none" }}
          >
            🎤
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

      {/* LIVEKIT VOICE MODAL */}
      {
        isVoiceActive && (
          <VoiceChat
            onClose={() => setIsVoiceActive(false)}
            onAction={refreshAll}
          />
        )
      }
    </>
  );
}
