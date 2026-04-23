import { useEffect, useState, useRef } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { PropagateLoader } from "react-spinners";

import Header from "./DashboardHeader";
import BentoGrid from "../../components/BentoGrid";
import { Meteors } from "../../components/ui/Meteors";
import Footer from "../../components/Footer";
import InvoiceForm from "../../components/InvoiceForm";

import { TIME_SLOTS, formatTime12h } from "../../utils/timeSlots";
import { COUNTRY_CODES } from "../../utils/countryCodes";

import "../../styles/dentist_dashboard.css";
import "../../styles/dashboard_extras.css";
import "../../styles/patient_dashboard.css";
import "../../styles/ai_features.css";
import "../../styles/invoice_form.css";

/* ==============================
   CONFIG
================================ */

const API = import.meta.env.VITE_API_BASE_URL?.replace(
  "http://",
  "https://"
);

/* ==============================
   HELPERS
================================ */

const getFlagEmoji = (isoCode) => {
  if (!isoCode) return "🌐";
  return isoCode
    .toUpperCase()
    .replace(/./g, (char) =>
      String.fromCodePoint(char.charCodeAt(0) + 127397)
    );
};

/* ==============================
   MEDICATION CONSTANTS
================================ */

const DENTAL_MEDICATIONS = [
  // Antibiotics
  { name: "Amoxicillin 500mg", type: "Antibiotic" },
  { name: "Augmentin 625mg", type: "Antibiotic" },
  { name: "Metronidazole 400mg", type: "Antibiotic" },
  { name: "Clindamycin 300mg", type: "Antibiotic" },
  { name: "Azithromycin 500mg", type: "Antibiotic" },
  { name: "Doxycycline 100mg", type: "Antibiotic" },

  // Pain Relief / NSAIDs
  { name: "Ibuprofen 400mg", type: "Pain Relief" },
  { name: "Ibuprofen 600mg", type: "Pain Relief" },
  { name: "Paracetamol 650mg", type: "Pain Relief" },
  { name: "Paracetamol 500mg", type: "Pain Relief" },
  { name: "Ketorol DT 10mg", type: "Pain Relief" },
  { name: "Ketorol 10mg", type: "Pain Relief" },
  { name: "Ketorolac 10mg", type: "Pain Relief" },
  { name: "Diclofenac 50mg", type: "Pain Relief" },
  { name: "Zerodol SP", type: "Pain Relief" },
  { name: "Combiflam", type: "Pain Relief" },
  { name: "Brufen 400mg", type: "Pain Relief" },
  { name: "Nimesulide 100mg", type: "Pain Relief" },

  // Antacids
  { name: "Pantoprazole 40mg", type: "Antacid" },
  { name: "Omeprazole 20mg", type: "Antacid" },
  { name: "Ranitidine 150mg", type: "Antacid" },

  // Topical & Mouthwash
  { name: "Chlorhexidine Mouthwash", type: "Mouthwash" },
  { name: "Hexigel", type: "Topical" },
  { name: "Betadine Gargle", type: "Mouthwash" },
  { name: "Dentogel", type: "Topical" },
  { name: "Orajel", type: "Topical" },

  // Steroids
  { name: "Dexamethasone 0.5mg", type: "Steroid" },
  { name: "Prednisolone 5mg", type: "Steroid" }
];

/* ==============================
   COMPONENT
================================ */

export default function DentistDashboard() {
  const { user, isLoaded } = useUser();
  const { session } = useSession();
  const navigate = useNavigate();

  /* ==============================
     STATE
  ================================ */

  const [pageLoading, setPageLoading] = useState(true);

  const [today, setToday] = useState([]);
  const [upcoming, setUpcoming] = useState([]);
  const [history, setHistory] = useState([]);

  const [aiOpen, setAiOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [profileVisible, setProfileVisible] = useState(false);

  // ===== INVOICES & BILLING STATE =====
  const [invoices, setInvoices] = useState([]);
  const [invoicePatient, setInvoicePatient] = useState("");
  const [editingInvoice, setEditingInvoice] = useState(null);

  // ===== ALL PATIENTS STATE =====
  const [patientsList, setPatientsList] = useState([]);
  const [patientPrescriptions, setPatientPrescriptions] = useState([]);

  // ===== PRESCRIPTIONS STATE =====
  const [prescPatient, setPrescPatient] = useState("");
  const [prescPatientSearch, setPrescPatientSearch] = useState("");
  const [prescMedications, setPrescMedications] = useState([{ name: "", dosage: "", duration: "" }]);
  const [prescNotes, setPrescNotes] = useState("");
  const [prescSubmitting, setPrescSubmitting] = useState(false);
  const [recentPrescriptions, setRecentPrescriptions] = useState([]);
  const [prescTreatmentPlan, setPrescTreatmentPlan] = useState("");
  const [prescRecommendations, setPrescRecommendations] = useState("");
  const [prescInstructions, setPrescInstructions] = useState("");
  const [prescMedSearch, setPrescMedSearch] = useState("");
  const [prescChiefComplaint, setPrescChiefComplaint] = useState("");

  const handleBulletKeyDown = (e, val, setter) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const cursorPosition = e.target.selectionStart;
      const textBefore = val.substring(0, cursorPosition);
      const textAfter = val.substring(cursorPosition);
      const newValue = textBefore + '\n• ' + textAfter;
      setter(newValue);
      
      // Reset cursor position after the bullet
      setTimeout(() => {
        e.target.selectionStart = e.target.selectionEnd = cursorPosition + 3;
      }, 0);
    }
  };

  const ensureFirstBullet = (val, setter) => {
    if (!val || val.trim() === "") {
      setter("• ");
    } else if (!val.startsWith("• ")) {
      setter("• " + val);
    }
  };
  const [visitType, setVisitType] = useState("complaint"); // 'complaint' or 'follow_up'
  const [prescContinue, setPrescContinue] = useState(false);
  const [prescXrays, setPrescXrays] = useState([]); // Array of filenames
  const [prescDate, setPrescDate] = useState(new Date().toISOString().split('T')[0]);
  const [showPrescPatientSuggestions, setShowPrescPatientSuggestions] = useState(false);
  const [prescPatientPhone, setPrescPatientPhone] = useState("");
  const [prescCountryCode, setPrescCountryCode] = useState("+91");
  const [showPrescCountrySearch, setShowPrescCountrySearch] = useState(false);

  // ===== ANALYTICS STATE =====
  const [reportDate, setReportDate] = useState(new Date().toISOString().split('T')[0]);
  const [reportView, setReportView] = useState("daily");

  // ===== HISTORY FILTER STATE =====
  const [historyNameFilter, setHistoryNameFilter] = useState("");
  const [historyDateFilter, setHistoryDateFilter] = useState("");
  const [historySortOrder, setHistorySortOrder] = useState("newest"); // 'newest' or 'oldest'

  /* ==============================
     AUTH & ACCESS CONTROL
  ================================ */

  useEffect(() => {
    if (!isLoaded) return;

    if (!user) {
      navigate("/login");
      return;
    }

    const role = user.publicMetadata?.role;
    const email = user.primaryEmailAddress?.emailAddress?.toLowerCase();

    const allowedEmails = [
      "prachi.swarnim@gmail.com",
      "choudhary.shruti01@gmail.com"
    ];

    const isDentist = role === "dentist" || allowedEmails.includes(email);

    if (!isDentist) {
      sessionStorage.removeItem("flossy_role");
      navigate(role === "receptionist" ? "/receptionist" : "/patient", {
        replace: true
      });
    }

    // Set page title with full name
    const fullNameTitle = `${user.firstName || ''} ${user.lastName || ''}`.trim() || 'Dentist';
    document.title = `Dr. ${fullNameTitle} | Dentist Dashboard - Smile Artists`;
  }, [isLoaded, user, navigate]);

  /* ==============================
     DATA LOADERS
  ================================ */

  async function loadAppointments() {
    const token = await session.getToken({ template: "default" });

    const res = await fetch(
      `${API}/api/appointments/dentist_upcoming`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );

    const data = await res.json();

    setToday(data.today || []);
    setUpcoming(data.upcoming || []);
    setHistory(data.history || []);
  }

  async function fetchPatients() {
    const token = await session.getToken({ template: "default" });
    const res = await fetch(`${API}/api/patients/`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      console.log("📊 Patients fetched:", data.length, data);
      // Backend already filters out staff members, just use the data
      setPatientsList(data);
    } else {
      console.error("❌ Failed to fetch patients:", res.status);
    }
  }

  async function fetchPatientPrescriptions(patientName) {
    if (!patientName) {
      setPatientPrescriptions([]);
      return;
    }
    const token = await session.getToken({ template: "default" });
    try {
      const res = await fetch(`${API}/api/prescriptions/patient/${encodeURIComponent(patientName)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPatientPrescriptions(data.prescriptions || []);
      }
    } catch (err) {
      console.error("Failed to fetch patient prescriptions:", err);
      setPatientPrescriptions([]);
    }
  }

  async function fetchInvoices() {
    const token = await session.getToken({ template: "default" });
    const res = await fetch(`${API}/api/invoices/history`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      setInvoices(data.invoices || []);
    }
  }

  async function fetchRecentPrescriptions() {
    const token = await session.getToken({ template: "default" });
    try {
      const res = await fetch(`${API}/api/prescriptions/recent`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setRecentPrescriptions(data.prescriptions || []);
      }
    } catch (err) {
      console.error("Failed to fetch prescriptions:", err);
    }
  }

  useEffect(() => {
    if (!isLoaded || !session) return;

    Promise.all([
      loadAppointments(),
      fetchPatients(),
      fetchInvoices(),
      fetchRecentPrescriptions()
    ])
      .catch(console.error)
      .finally(() => setPageLoading(false));
  }, [isLoaded, session]);

  /* ==============================
     INVOICE DOWNLOAD
  ================================ */

  async function handleXrayUpload(e) {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    const token = await session.getToken({ template: "default" });
    const uploadedNames = [...prescXrays];

    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch(`${API}/api/prescriptions/upload_xray`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData
        });
        if (res.ok) {
          const data = await res.json();
          uploadedNames.push(data.filename);
        }
      } catch (err) {
        console.error("X-ray upload failed:", err);
      }
    }
    setPrescXrays(uploadedNames);
  }

  async function downloadInvoice(id, invNum, stamp = true, patientName = "") {
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
  }

  /* ==============================
     PRESCRIPTION HANDLERS
  ================================ */

  function addMedication() {
    setPrescMedications([...prescMedications, { name: "", dosage: "", duration: "" }]);
  }

  function removeMedication(idx) {
    setPrescMedications(prescMedications.filter((_, i) => i !== idx));
  }

  function updateMedication(idx, field, value) {
    const updated = [...prescMedications];
    updated[idx][field] = value;
    setPrescMedications(updated);
  }

  async function submitPrescription() {
    if (!prescPatient) return alert("Please select a patient.");

    setPrescSubmitting(true);
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/prescriptions/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          patient_name: prescPatient,
          details: prescChiefComplaint,
          diagnosis: prescNotes,
          treatment_plan: prescTreatmentPlan,
          recommendations: prescRecommendations,
          instructions: prescInstructions,
          medications: prescMedications.filter(m => m.name),
          doctor_name: fullName,
          continue_prescription_id: prescContinue && patientPrescriptions.length > 0 ? patientPrescriptions[0].id : null,
          xrays: prescXrays,
          created_at: prescDate ? new Date(prescDate).toISOString() : new Date().toISOString()
        })
      });

      if (res.ok) {
        alert("Prescription uploaded successfully!");
        setPrescPatient("");
        setPrescPatientSearch("");
        setPrescMedications([{ name: "", dosage: "", duration: "" }]);
        setPrescNotes("");
        setPrescTreatmentPlan("");
        setPrescRecommendations("");
        setPrescInstructions("");
        setPrescMedSearch("");
        setPrescChiefComplaint("");
        setPrescContinue(false);
        setPrescXrays([]);
        setPrescDate(new Date().toISOString().split('T')[0]);
        fetchRecentPrescriptions();
      } else {
        const errData = await res.json();
        alert("Error: " + (errData.detail || "Failed to create prescription"));
      }
    } catch (err) {
      console.error("Prescription error:", err);
      alert("Failed to create prescription.");
    } finally {
      setPrescSubmitting(false);
    }
  }

  async function downloadPrescription(id, patientName = "", stamp = true) {
    const token = await session.getToken({ template: "default" });
    const res = await fetch(`${API}/api/prescriptions/${id}/pdf?stamp=${stamp}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const safeName = patientName ? patientName.replace(/[^a-zA-Z0-9]/g, "_") : "patient";
      a.download = `${safeName}_prescription${stamp ? "" : "_plain"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
  }

  async function deletePrescription(id) {
    if (!window.confirm("Are you sure you want to delete this prescription? This cannot be undone.")) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/prescriptions/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        alert("Prescription deleted successfully.");
        fetchPatientPrescriptions(prescPatient);
        fetchRecentPrescriptions();
      } else {
        alert("Failed to delete prescription.");
      }
    } catch (err) {
      console.error("Delete prescription error:", err);
      alert("Error deleting prescription.");
    }
  }

  async function deleteInvoice(id) {
    if (!window.confirm("Are you sure you want to delete this invoice? This cannot be undone.")) return;
    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/invoices/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        alert("Invoice deleted successfully.");
        fetchInvoices();
      } else {
        alert("Failed to delete invoice.");
      }
    } catch (err) {
      console.error("Delete invoice error:", err);
      alert("Error deleting invoice.");
    }
  }

  /* ==============================
     HELPERS
  ================================ */

  function capitalizeFullName(email = "") {
    const name = email.split("@")[0];
    return name
      .split(/[._-]/)
      .map(
        p => p.charAt(0).toUpperCase() + p.slice(1).toLowerCase()
      )
      .join(" ");
  }

  const fullName =
    user?.fullName ||
    capitalizeFullName(
      user?.primaryEmailAddress?.emailAddress
    ) ||
    "Doctor";

  // Filtered patients for prescription search
  const filteredPatients = patientsList.filter(p =>
    p.name?.toLowerCase().includes(prescPatientSearch.toLowerCase())
  );

  /* ==============================
     AI CHAT HANDLER
  ================================ */

  async function sendAiMessage(customMsg = null) {
    const msg = customMsg || input.trim();
    if (!msg) return;

    setMessages(prev => [...prev, { from: "user", text: msg }]);
    setInput("");
    setTyping(true);

    try {
      const token = await session.getToken({ template: "default" });
      const res = await fetch(`${API}/api/ai/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ message: msg, context: "dentist_dashboard" })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { from: "ai", text: data.response || data.message || "I'm here to help!" }]);
    } catch (err) {
      console.error("AI Error:", err);
      setMessages(prev => [...prev, { from: "ai", text: "Sorry, I couldn't process that. Please try again." }]);
    } finally {
      setTyping(false);
    }
  }

  /* ==============================
     LOADING STATE
  ================================ */

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

  /* ==============================
     RENDER
  ================================ */

  return (
    <div className={`dashboard-shell relative overflow-hidden ${!profileVisible ? "sidebar-collapsed" : "sidebar-expanded"}`}>
      {/* Animated Premium Background Effects */}
      <Meteors number={25} />
      <div
        className="absolute top-0 right-0 w-[600px] h-[600px] pointer-events-none opacity-30"
        style={{
          background: "radial-gradient(circle at center, rgba(212,175,55,0.06) 0%, transparent 60%)",
        }}
      />
      <div
        className="absolute bottom-0 left-0 w-[600px] h-[600px] pointer-events-none opacity-30"
        style={{
          background: "radial-gradient(circle at center, rgba(212,175,55,0.04) 0%, transparent 60%)",
        }}
      />
      {/* DOCTOR PROFILE SIDEBAR (FULL HEIGHT) */}
      <aside className="profile-sidebar full-height">
        <div className="sidebar-top-icons">
          <div className="sidebar-icon-btn" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} title="Home">
            <i className="fas fa-home"></i>
          </div>
          <div className="sidebar-icon-btn" onClick={() => document.getElementById('appointments')?.scrollIntoView({ behavior: 'smooth' })} title="Appointments">
            <i className="fas fa-calendar-alt"></i>
          </div>
          <div className="sidebar-icon-btn" onClick={() => document.getElementById('history')?.scrollIntoView({ behavior: 'smooth' })} title="History">
            <i className="fas fa-history"></i>
          </div>
          <div className="sidebar-icon-btn" onClick={() => document.getElementById('analytics')?.scrollIntoView({ behavior: 'smooth' })} title="Analytics">
            <i className="fas fa-chart-line"></i>
          </div>
          <div className="sidebar-icon-btn" onClick={() => setAiOpen(true)} title="FlossyAI">
            <i className="fas fa-robot"></i>
          </div>
        </div>

        <div className="sidebar-bottom-section">
          <div className="profile-avatar-mini" title={`Dr. ${fullName}`}>
            {user?.imageUrl ? (
              <img src={user.imageUrl} alt="Profile" />
            ) : (
              <div className="avatar-placeholder-mini">
                <i className="fas fa-user-md"></i>
              </div>
            )}
          </div>
          <div 
             className="sidebar-logout-btn" 
             onClick={() => signOut(() => (window.location.href = "/"))}
             title="Logout"
          >
            <i className="fas fa-sign-out-alt"></i>
          </div>
        </div>
      </aside>

      <Header openAI={() => setAiOpen(true)} />
      <div className="dashboard-main-content">
        <main className="dentist-main">
          <h2 id="Message">Welcome back, Dr. {fullName}</h2>

          <div className="dashboard-layout" style={{ display: "flex", flexDirection: "column", gap: "1.5rem", paddingBottom: "1.5rem" }}>

            {/* ROW 1: APPOINTMENTS (SIDE BY SIDE) */}
            <div id="appointments" className="row-appointments" style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "1rem", width: "100%", maxWidth: "1020px", margin: "0 auto" }}>

              {/* TODAY */}
              <div className="card animate-fade-up" style={{ animationDelay: "0.1s", flex: "1", minWidth: "300px" }}>
                <div className="card-header">
                  <h3>Today's Appointments</h3>
                  <i className="fas fa-calendar-check card-icon"></i>
                </div>
                {today.length ? (
                  today.map((a) => (
                    <div className="appt-item" key={a.id}>
                      <b>
                        {new Date(a.time).toLocaleDateString()} {new Date(a.time).toLocaleTimeString("en-IN", {
                          hour: "2-digit",
                          minute: "2-digit",
                          hour12: true
                        })}
                      </b>
                      <div className="appt-patient">{a.patient_name || a.patient}</div>
                      <div className="appt-reason">{a.reason}</div>
                    </div>
                  ))
                ) : (
                  <p style={{ color: "#888", fontStyle: "italic" }}>No appointments today</p>
                )}
              </div>

              {/* UPCOMING */}
              <div className="card animate-fade-up" style={{ animationDelay: "0.2s", flex: "1", minWidth: "300px" }}>
                <div className="card-header">
                  <h3>Upcoming Appointments</h3>
                  <i className="fas fa-calendar-alt card-icon"></i>
                </div>
                {upcoming.length ? (
                  upcoming.slice(0, 5).map((a) => (
                    <div className="appt-item" key={a.id}>
                      <b>
                        {new Date(a.time).toLocaleDateString()} {new Date(a.time).toLocaleTimeString("en-IN", {
                          hour: "2-digit",
                          minute: "2-digit",
                          hour12: true
                        })}
                      </b>
                      <div className="appt-patient">{a.patient_name || a.patient}</div>
                      <div className="appt-reason">{a.reason}</div>
                    </div>
                  ))
                ) : (
                  <p style={{ color: "#888", fontStyle: "italic" }}>No upcoming appointments</p>
                )}
              </div>
            </div>

            {/* ROW 2: HISTORY */}
            <div className="row-history" style={{ display: "flex", justifyContent: "center" }}>
              <div className="card animate-fade-up" style={{ animationDelay: "0.3s", width: "100%", maxWidth: "1020px" }}>
                <div className="card-header">
                  <h3>Appointment History</h3>
                  <i className="fas fa-history card-icon"></i>
                </div>

                {/* HISTORY FILTERS */}
                <div style={{ display: "flex", gap: "10px", padding: "1rem", flexWrap: "wrap", borderBottom: "1px solid #333" }}>
                  <div style={{ flex: 1, minWidth: "200px" }}>
                    <label style={{ color: "#888", fontSize: "0.8rem", display: "block", marginBottom: "5px" }}>Search by Name</label>
                    <div className="input-icon-wrapper">
                      <i className="fas fa-search"></i>
                      <input
                        type="text"
                        placeholder="Patient name..."
                        value={historyNameFilter}
                        onChange={(e) => setHistoryNameFilter(e.target.value)}
                        className="dashboard-input"
                        style={{ padding: "10px" }}
                      />
                    </div>
                  </div>
                  <div style={{ flex: 1, minWidth: "200px" }}>
                    <label style={{ color: "#888", fontSize: "0.8rem", display: "block", marginBottom: "5px" }}>Filter by Date</label>
                    <div className="input-icon-wrapper">
                      <i className="fas fa-calendar-alt" onClick={(e) => {
                        const input = e.currentTarget.parentElement.querySelector('input');
                        if (input) input.showPicker();
                      }} style={{ cursor: 'pointer', pointerEvents: 'auto' }}></i>
                      <input
                        type="date"
                        value={historyDateFilter}
                        onChange={(e) => setHistoryDateFilter(e.target.value)}
                        onClick={(e) => e.target.showPicker()}
                        className="dashboard-input"
                        style={{ padding: "10px", colorScheme: "dark" }}
                      />
                    </div>
                  </div>
                  <div style={{ flex: 1, minWidth: "150px" }}>
                    <label style={{ color: "#888", fontSize: "0.8rem", display: "block", marginBottom: "5px" }}>Sort Order</label>
                    <select
                      value={historySortOrder}
                      onChange={(e) => setHistorySortOrder(e.target.value)}
                      className="dashboard-input"
                      style={{ padding: "10px", width: "100%", height: "40px", background: "#222", border: "1px solid #333", borderRadius: "5px", colorScheme: "dark" }}
                    >
                      <option value="newest">Newest First</option>
                      <option value="oldest">Oldest First</option>
                      <option value="az">Patient Name (A-Z)</option>
                      <option value="za">Patient Name (Z-A)</option>
                    </select>
                  </div>
                  {(historyNameFilter || historyDateFilter) && (
                    <button
                      onClick={() => { setHistoryNameFilter(""); setHistoryDateFilter(""); }}
                      style={{ alignSelf: "flex-end", padding: "10px 15px", background: "#555", border: "none", borderRadius: "5px", color: "#fff", cursor: "pointer" }}
                    >
                      <i className="fas fa-times"></i> Clear
                    </button>
                  )}
                </div>

                {history.length ? (
                  <div style={{ maxHeight: "300px", overflowY: "auto", padding: "0.5rem" }} className="elegant-scroll">
                    {history
                      .filter(a => {
                        const nameMatch = !historyNameFilter || (a.patient || a.patient_name || "").toLowerCase().includes(historyNameFilter.toLowerCase());
                        const dateMatch = !historyDateFilter || new Date(a.time).toISOString().split('T')[0] === historyDateFilter;
                        return nameMatch && dateMatch;
                      })
                      .sort((a, b) => {
                        if (historySortOrder === "az") {
                          return (a.patient || a.patient_name || "").localeCompare(b.patient || b.patient_name || "");
                        }
                        if (historySortOrder === "za") {
                          return (b.patient || b.patient_name || "").localeCompare(a.patient || a.patient_name || "");
                        }
                        const dateA = new Date(a.time);
                        const dateB = new Date(b.time);
                        return historySortOrder === "newest" ? dateB - dateA : dateA - dateB;
                      })
                      .map((a) => (
                        <div className="appt-item" key={a.id} style={{ opacity: 0.8 }}>
                          <b>
                            {new Date(a.time).toLocaleDateString()} {new Date(a.time).toLocaleTimeString("en-IN", {
                              hour: "2-digit",
                              minute: "2-digit",
                              hour12: true
                            })}
                          </b>
                          <div className="appt-patient">{a.patient || a.patient_name}</div>
                          <div className="appt-reason">{a.reason}</div>
                          {a.completed && <span className="completed-tag">Completed</span>}
                          {a.status === "completed" && <span className="completed-tag">Completed</span>}
                          {a.status === "missed" && <span style={{ color: "#e74c3c", fontSize: "0.8rem" }}>Not Visited</span>}
                        </div>
                      ))}
                    {history.filter(a => {
                      const nameMatch = !historyNameFilter || (a.patient || a.patient_name || "").toLowerCase().includes(historyNameFilter.toLowerCase());
                      const dateMatch = !historyDateFilter || new Date(a.time).toISOString().split('T')[0] === historyDateFilter;
                      return nameMatch && dateMatch;
                    }).length === 0 && (
                        <p style={{ color: "#888", textAlign: "center", padding: "2rem" }}>No matching appointments found.</p>
                      )}
                  </div>
                ) : (
                  <p style={{ color: "#888", textAlign: "center", padding: "2rem" }}>No history found.</p>
                )}
              </div>
            </div>

            {/* ROW 3: ANALYTICS (FULL WIDTH) */}
            <div id="analytics" className="row-analytics" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
              <div className="card animate-fade-up" style={{ animationDelay: "0.4s", width: "100%", maxWidth: "1020px" }}>
                <div className="card-header">
                  <div style={{ display: "flex", alignItems: "center", gap: "15px" }}>
                    <h3>Visit Analytics</h3>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <div className="input-icon-wrapper" style={{ display: "inline-flex", height: "40px" }}>
                        <i
                          className="fas fa-calendar-alt"
                          onClick={(e) => {
                            const input = e.currentTarget.parentElement.querySelector('input');
                            if (input) input.showPicker();
                          }}
                          style={{ cursor: 'pointer', pointerEvents: 'auto' }}
                        ></i>
                        <input
                          type="date"
                          value={reportDate}
                          onChange={(e) => setReportDate(e.target.value)}
                          className="dashboard-input"
                          style={{ border: "1px solid #444", height: "100%", width: "160px" }}
                          onClick={(e) => e.target.showPicker()}
                        />
                      </div>
                      <div className="tab-group" style={{ display: "flex", background: "rgba(255,255,255,0.05)", borderRadius: "8px", padding: "3px", border: "1px solid #444", gap: "2px" }}>
                        {['daily', 'monthly', 'yearly'].map(view => (
                          <button
                            key={view}
                            onClick={() => setReportView(view)}
                            style={{
                              padding: "6px 18px",
                              borderRadius: "6px",
                              border: "none",
                              fontSize: "0.85rem",
                              cursor: "pointer",
                              background: reportView === view ? "#f0b800" : "transparent",
                              color: reportView === view ? "#000" : "#888",
                              fontWeight: reportView === view ? "700" : "500",
                              transition: "all 0.2s ease",
                              textTransform: "capitalize"
                            }}
                          >
                            {view}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                  <i className="fas fa-chart-line card-icon"></i>
                </div>
                <div style={{ padding: "1rem" }}>
                  {/* METRICS CARDS */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
                    <div className="stat-card glow-card">
                      <h4>Appointments Done</h4>
                      <div className="stat-value" style={{ color: "#2ecc71" }}>
                        {[...today, ...history].filter(a => {
                          const d = new Date(a.time);
                          const r = new Date(reportDate);
                          if (a.status !== 'completed') return false;
                          if (reportView === 'daily') return d.toDateString() === r.toDateString();
                          if (reportView === 'monthly') return d.getMonth() === r.getMonth() && d.getFullYear() === r.getFullYear();
                          if (reportView === 'yearly') return d.getFullYear() === r.getFullYear();
                          return false;
                        }).length}
                      </div>
                    </div>
                    <div className="stat-card glow-card" style={{ animationDelay: '0.1s' }}>
                      <h4>Filtered Revenue</h4>
                      <div className="stat-value" style={{ color: "#d4af37" }}>
                        ₹{invoices
                          .filter(inv => {
                            const d = new Date(inv.date);
                            const r = new Date(reportDate);
                            if (reportView === 'daily') return d.toDateString() === r.toDateString();
                            if (reportView === 'monthly') return d.getMonth() === r.getMonth() && d.getFullYear() === r.getFullYear();
                            if (reportView === 'yearly') return d.getFullYear() === r.getFullYear();
                            return false;
                          })
                          .reduce((sum, inv) => sum + (parseFloat(inv.total) || 0), 0)
                          .toLocaleString("en-IN")}
                      </div>
                    </div>
                    <div className="stat-card glow-card" style={{ animationDelay: '0.2s' }}>
                      <h4>Total Patients</h4>
                      <div className="stat-value" style={{ color: "#3498db" }}>
                        {patientsList.length}
                      </div>
                    </div>
                    <div className="stat-card glow-card" style={{ animationDelay: '0.3s' }}>
                      <h4>Prescriptions</h4>
                      <div className="stat-value" style={{ color: "#9b59b6" }}>
                        {recentPrescriptions.length}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* ROW 4: PRESCRIPTIONS */}
            <div className="row-prescriptions" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
              <div className="card animate-fade-up premium-form" style={{ animationDelay: "0.5s", width: "100%", maxWidth: "1020px" }}>
                <div style={{ padding: "0.5rem" }}>
                  <div className="card-header" style={{ marginBottom: '1.5rem' }}>
                    <h3>Create Prescription</h3>
                    <i className="fas fa-file-prescription card-icon"></i>
                  </div>

                  {/* PATIENT & DATE SELECTION */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1rem" }}>
                    {/* SELECT PATIENT */}
                    <div style={{ position: "relative" }}>
                      <label>Select Patient</label>
                      <div className="patient-search-container" style={{ position: "relative" }}>
                        <div className="input-icon-wrapper" style={{ height: "45px" }}>
                          <i className="fas fa-search"></i>
                          <input
                            type="text"
                            placeholder="Search patient name..."
                            value={prescPatientSearch || prescPatient}
                            onChange={(e) => {
                              setPrescPatientSearch(e.target.value);
                              setShowPrescPatientSuggestions(true);
                              if (prescPatient) setPrescPatient("");
                            }}
                            onFocus={() => setShowPrescPatientSuggestions(true)}
                            className="dashboard-input"
                            style={{ height: "100%" }}
                          />
                        </div>

                        {showPrescPatientSuggestions && (prescPatientSearch.trim() !== "" || patientsList.length > 0) && (
                          <div className="patient-suggestions elegant-scroll" style={{
                            position: "absolute", top: "100%", left: 0, right: 0,
                            zIndex: 101, background: "#1a1a1a", border: "1px solid #444",
                            borderRadius: "8px", marginTop: "5px", maxHeight: "180px",
                            overflowY: "auto", boxShadow: "0 10px 25px rgba(0,0,0,0.5)"
                          }}>
                            {patientsList
                              .filter(p => (p.name || "").toLowerCase().includes((prescPatientSearch || "").toLowerCase()))
                              .map(p => (
                                <div
                                  key={p.id}
                                  onClick={() => {
                                    setPrescPatient(p.name);
                                    setPrescPatientSearch(p.name);
                                    fetchPatientPrescriptions(p.name);
                                    // Auto-fill phone
                                    setPrescPatientPhone(p.phone || "");
                                    setShowPrescPatientSuggestions(false);
                                  }}
                                  style={{
                                    padding: "10px 15px", cursor: "pointer", borderBottom: "1px solid #333",
                                    color: "#fff", background: prescPatient === p.name ? "#2a2a2a" : "transparent"
                                  }}
                                >
                                  {p.name}
                                </div>
                              ))}
                          </div>
                        )}
                        {showPrescPatientSuggestions && (
                          <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 100 }} onClick={() => setShowPrescPatientSuggestions(false)}></div>
                        )}
                      </div>
                    </div>

                    {/* PRESCRIPTION DATE */}
                    <div className="form-group">
                      <label>Prescription Date</label>
                      <div className="input-icon-wrapper" style={{ height: "45px" }}>
                        <i
                          className="fas fa-calendar-alt"
                          onClick={(e) => {
                            const input = e.currentTarget.parentElement.querySelector('input');
                            if (input) input.showPicker();
                          }}
                          style={{ cursor: 'pointer', pointerEvents: 'auto' }}
                        ></i>
                        <input
                          type="date"
                          value={prescDate}
                          onChange={(e) => setPrescDate(e.target.value)}
                          className="dashboard-input"
                          style={{ height: "100%" }}
                          onClick={(e) => e.target.showPicker()}
                        />
                      </div>
                    </div>
                  </div>

                  {/* PATIENT PHONE & COUNTRY CODE */}
                  <div className="form-group" style={{ marginBottom: "1.5rem" }}>
                    <label>Patient Phone Number</label>
                    <div style={{ display: "flex", gap: "10px", position: "relative" }}>
                      <div className="input-icon-wrapper" style={{ width: "120px", height: "45px" }}>
                        <i className="fas fa-globe"></i>
                        <input
                          type="text"
                          placeholder="Code"
                          value={prescCountryCode}
                          onChange={(e) => {
                            setPrescCountryCode(e.target.value);
                            setShowPrescCountrySearch(true);
                          }}
                          onFocus={() => setShowPrescCountrySearch(true)}
                          className="dashboard-input"
                          style={{ width: "100%", height: "100%" }}
                        />
                        {showPrescCountrySearch && (
                          <div className="elegant-scroll" style={{
                            position: "absolute", top: "100%", left: 0, right: 0,
                            zIndex: 105, background: "#1a1a1a", border: "1px solid #444",
                            borderRadius: "8px", marginTop: "5px", maxHeight: "200px",
                            overflowY: "auto", boxShadow: "0 10px 25px rgba(0,0,0,0.5)", width: "220px"
                          }}>
                            {COUNTRY_CODES
                              .filter(c =>
                                c.code.includes(prescCountryCode) ||
                                c.iso.toLowerCase().includes(prescCountryCode.toLowerCase()) ||
                                c.name.toLowerCase().includes(prescCountryCode.toLowerCase())
                              )
                              .map(c => (
                                <div key={c.iso} onClick={() => { setPrescCountryCode(c.code); setShowPrescCountrySearch(false); }}
                                  style={{ padding: "10px", cursor: "pointer", borderBottom: "1px solid #333", color: "#fff", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "8px" }}>
                                  <span style={{ fontSize: "1.2rem" }}>{getFlagEmoji(c.iso)}</span>
                                  <span>{c.name} ({c.code})</span>
                                </div>
                              ))}
                          </div>
                        )}
                        {showPrescCountrySearch && (
                          <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 104 }} onClick={() => setShowPrescCountrySearch(false)}></div>
                        )}
                      </div>
                      <input
                        type="text"
                        placeholder="Phone number"
                        value={prescPatientPhone}
                        onChange={(e) => setPrescPatientPhone(e.target.value)}
                        className="dashboard-input"
                        style={{ flex: 1, height: "45px" }}
                      />
                    </div>
                  </div>

                   {/* CHIEF COMPLAINT */}
                   <div style={{ marginBottom: "1.5rem" }}>
                     <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                       <label style={{ color: "#f0b800", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "1px", fontSize: "0.85rem" }}>Chief Complaint</label>
                       
                       {/* Visit Type Slider */}
                       <div style={{ display: "flex", background: "#222", borderRadius: "20px", padding: "2px", border: "1px solid #444" }}>
                         <button 
                           onClick={() => { setVisitType("complaint"); if(prescChiefComplaint === "Follow up") setPrescChiefComplaint(""); }}
                           style={{ 
                             padding: "4px 12px", borderRadius: "18px", border: "none", cursor: "pointer", fontSize: "0.7rem", fontWeight: "bold",
                             background: visitType === "complaint" ? "linear-gradient(135deg, #f0b800, #b8860b)" : "transparent",
                             color: visitType === "complaint" ? "#000" : "#888",
                             transition: "all 0.3s ease"
                           }}
                         >Complaint</button>
                         <button 
                           onClick={() => { setVisitType("follow_up"); setPrescChiefComplaint("Follow up"); }}
                           style={{ 
                             padding: "4px 12px", borderRadius: "18px", border: "none", cursor: "pointer", fontSize: "0.7rem", fontWeight: "bold",
                             background: visitType === "follow_up" ? "linear-gradient(135deg, #f0b800, #b8860b)" : "transparent",
                             color: visitType === "follow_up" ? "#000" : "#888",
                             transition: "all 0.3s ease"
                           }}
                         >Follow Up</button>
                       </div>
                     </div>
                     <textarea
                       placeholder="e.g. Pain in lower left molar for 3 days..."
                       value={prescChiefComplaint || ""}
                       onFocus={() => ensureFirstBullet(prescChiefComplaint, setPrescChiefComplaint)}
                       onKeyDown={(e) => handleBulletKeyDown(e, prescChiefComplaint, setPrescChiefComplaint)}
                       onChange={(e) => {
                         setPrescChiefComplaint(e.target.value);
                         if (e.target.value !== "Follow up" && visitType === "follow_up") setVisitType("complaint");
                       }}
                       style={{
                         width: "100%",
                         padding: "10px",
                         background: "#222",
                         border: "1px solid #444",
                         borderRadius: "6px",
                         color: "#fff",
                         fontSize: "0.85rem",
                         minHeight: "60px",
                         resize: "vertical"
                       }}
                     ></textarea>
                   </div>

                  {/* DIAGNOSIS & TREATMENT PLAN - Side by Side */}
                   <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
                    <div>
                      <label>Diagnosis</label>
                      <textarea
                        placeholder="e.g. Chronic Gingivitis..."
                        value={prescNotes || ""}
                        onFocus={() => ensureFirstBullet(prescNotes, setPrescNotes)}
                        onKeyDown={(e) => handleBulletKeyDown(e, prescNotes, setPrescNotes)}
                        onChange={(e) => setPrescNotes(e.target.value)}
                        className="dashboard-textarea"
                        style={{ minHeight: "100px" }}
                      ></textarea>
                    </div>
                    <div>
                      <label>Treatment Plan</label>
                      <textarea
                        placeholder="e.g. Scaling and Root Planing..."
                        value={prescTreatmentPlan || ""}
                        onFocus={() => ensureFirstBullet(prescTreatmentPlan, setPrescTreatmentPlan)}
                        onKeyDown={(e) => handleBulletKeyDown(e, prescTreatmentPlan, setPrescTreatmentPlan)}
                        onChange={(e) => setPrescTreatmentPlan(e.target.value)}
                        className="dashboard-textarea"
                        style={{ minHeight: "100px" }}
                      ></textarea>
                    </div>
                  </div>

                  {/* Rx - MEDICATIONS */}
                  <div style={{ marginBottom: "1.5rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                      <label style={{ display: "flex", alignItems: "center" }}>
                        <span style={{ fontFamily: "Times New Roman, serif", fontStyle: "italic", fontSize: "1.42rem", color: "#d4af37", marginRight: "8px", fontWeight: "bold" }}>Rx</span>
                      </label>
                      <div style={{ position: "relative", width: "250px" }}>
                        <div className="input-icon-wrapper">
                          <i className="fas fa-search"></i>
                          <input
                            type="text"
                            placeholder="Quick search..."
                            value={prescMedSearch || ""}
                            onChange={(e) => setPrescMedSearch(e.target.value)}
                            className="dashboard-input"
                          />
                        </div>
                        {/* Medication Suggestions Dropdown */}
                        {prescMedSearch && prescMedSearch.length > 0 && (
                          <div className="elegant-scroll" style={{
                            position: "absolute",
                            top: "100%",
                            left: 0,
                            right: 0,
                            background: "#2a2a2a",
                            border: "1px solid #555",
                            borderTop: "none",
                            borderRadius: "0 0 5px 5px",
                            maxHeight: "200px",
                            overflowY: "auto",
                            zIndex: 100,
                            boxShadow: "0 4px 12px rgba(0,0,0,0.5)"
                          }}>
                            {DENTAL_MEDICATIONS
                              .filter(med => med.name.toLowerCase().includes(prescMedSearch.toLowerCase()))
                              .map((med, idx) => (
                                <div
                                  key={idx}
                                  onClick={() => {
                                    // Add medication to recommendations
                                    setPrescRecommendations(prev =>
                                      prev ? `${prev}\n• ${med.name}` : `• ${med.name}`
                                    );
                                    setPrescMedSearch("");
                                  }}
                                  style={{
                                    padding: "10px 15px",
                                    cursor: "pointer",
                                    borderBottom: "1px solid #444",
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center"
                                  }}
                                  onMouseOver={(e) => e.currentTarget.style.background = "#3a3a3a"}
                                  onMouseOut={(e) => e.currentTarget.style.background = "transparent"}
                                >
                                  <span style={{ color: "#fff" }}>{med.name}</span>
                                  <span style={{
                                    color: "#f0b800",
                                    fontSize: "0.75rem",
                                    background: "#333",
                                    padding: "2px 8px",
                                    borderRadius: "10px"
                                  }}>{med.type}</span>
                                </div>
                              ))
                            }
                            {DENTAL_MEDICATIONS.filter(med => med.name.toLowerCase().includes(prescMedSearch.toLowerCase())).length === 0 && (
                              <div style={{ padding: "10px 15px", color: "#888", fontSize: "0.85rem" }}>
                                No matching medications. You can still type in the recommendations.
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    <textarea
                      placeholder="e.g. Tab. Paracetamol 500mg - 1-0-1 for 3 days..."
                      value={prescRecommendations || ""}
                      onFocus={() => ensureFirstBullet(prescRecommendations, setPrescRecommendations)}
                      onKeyDown={(e) => handleBulletKeyDown(e, prescRecommendations, setPrescRecommendations)}
                      onChange={(e) => setPrescRecommendations(e.target.value)}
                      className="dashboard-textarea"
                      style={{ minHeight: "100px" }}
                    ></textarea>
                  </div>

                  {/* RECOMMENDATION / INSTRUCTIONS */}
                  <div style={{ marginBottom: "1.5rem" }}>
                    <label style={{ color: "#f0b800", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "1px", fontSize: "0.85rem" }}>Recommendation / Instructions</label>
                    <textarea
                      placeholder="e.g. Warm saline rinses 3 times a day, avoid chewing on the right side..."
                      value={prescInstructions || ""}
                      onFocus={() => ensureFirstBullet(prescInstructions, setPrescInstructions)}
                      onKeyDown={(e) => handleBulletKeyDown(e, prescInstructions, setPrescInstructions)}
                      onChange={(e) => setPrescInstructions(e.target.value)}
                      className="dashboard-textarea"
                      style={{ minHeight: "100px" }}
                    ></textarea>
                  </div>

                  {/* X-RAY UPLOAD SECTION */}
                  <div style={{ marginBottom: "1.5rem" }}>
                    <label>Radiological Attachments (X-Rays)</label>
                    <div style={{
                      border: "2px dashed rgba(212, 175, 55, 0.2)",
                      borderRadius: "12px",
                      padding: "2.5rem 1.5rem",
                      textAlign: "center",
                      background: "rgba(0,0,0,0.2)",
                      cursor: "pointer",
                      position: "relative",
                      transition: "all 0.3s ease",
                    }}
                      onMouseEnter={(e) => e.currentTarget.style.borderColor = "#d4af37"}
                      onMouseLeave={(e) => e.currentTarget.style.borderColor = "rgba(212, 175, 55, 0.2)"}
                      onClick={() => document.getElementById("xray-input").click()}
                    >
                      <i className="fas fa-cloud-upload-alt" style={{ fontSize: "2.5rem", color: "#d4af37", opacity: 0.8, marginBottom: "12px" }}></i>
                      <p style={{ color: "#aaa", fontSize: "0.9rem", margin: 0 }}>Click or drag to upload X-ray photos</p>
                      <input
                        id="xray-input"
                        type="file"
                        multiple
                        accept="image/*"
                        onChange={handleXrayUpload}
                        style={{ display: "none" }}
                      />
                    </div>

                    {/* X-ray Previews */}
                    {prescXrays.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", marginTop: "15px" }}>
                        {prescXrays.map((name, idx) => (
                          <div key={idx} style={{ position: "relative", width: "80px", height: "80px" }}>
                            <img
                              src={`${API}/uploads/${name}`}
                              alt="X-ray"
                              style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "6px", border: "1px solid #444" }}
                            />
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setPrescXrays(prev => prev.filter((_, i) => i !== idx));
                              }}
                              style={{
                                position: "absolute", top: "-5px", right: "-5px",
                                background: "#ff4d4d", color: "#fff", border: "none",
                                borderRadius: "50%", width: "20px", height: "20px",
                                fontSize: "10px", cursor: "pointer", display: "flex",
                                alignItems: "center", justifyContent: "center",
                                boxShadow: "0 2px 4px rgba(0,0,0,0.3)"
                              }}
                            >
                              <i className="fas fa-times"></i>
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* CONTINUE PRESCRIPTION TOGGLE */}
                  {prescPatient && patientPrescriptions.length > 0 && (
                    <div style={{
                      display: "flex", alignItems: "center", gap: "12px",
                      padding: "1rem", marginBottom: "1.5rem",
                      background: "rgba(46, 204, 113, 0.05)", 
                      border: "1px solid rgba(46, 204, 113, 0.2)",
                      borderRadius: "12px", cursor: "pointer",
                      transition: "all 0.2s ease"
                    }}
                      onClick={() => setPrescContinue && setPrescContinue(!prescContinue)}
                    >
                      <input
                        type="checkbox"
                        checked={prescContinue || false}
                        onChange={(e) => setPrescContinue(e.target.checked)}
                        style={{ accentColor: "#2ecc71", width: "18px", height: "18px", cursor: "pointer" }}
                      />
                      <div>
                        <span style={{ color: "#2ecc71", fontWeight: "700", fontSize: "0.9rem" }}>Continue Last Prescription</span>
                        <div style={{ color: "#777", fontSize: "0.8rem", marginTop: "2px" }}>This visit will be appended as a new page to the patient's latest prescription PDF</div>
                      </div>
                    </div>
                  )}

                  {/* UPLOAD PRESCRIPTION BUTTON */}
                  <button
                    onClick={submitPrescription}
                    disabled={prescSubmitting || !prescPatient}
                    className="upload-btn"
                    style={{
                        width: 'calc(100% + 1rem)',
                        marginLeft: '-0.5rem',
                        marginRight: '-0.5rem',
                        marginBottom: '-0.5rem',
                        borderRadius: '0 0 12px 12px',
                        marginTop: '1rem'
                    }}
                  >
                    {prescSubmitting ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-cloud-upload-alt"></i>}
                    {prescSubmitting ? " UPLOADING..." : " UPLOAD PRESCRIPTION"}
                  </button>

                  {/* PATIENT PRESCRIPTION HISTORY - Below Upload Button */}
                  {prescPatient && patientPrescriptions.length > 0 && (
                    <div style={{ marginTop: "1.5rem", background: "#222", borderRadius: "8px", border: "1px solid #444", padding: "1rem" }}>
                      <h4 style={{ color: "#f0b800", marginBottom: "10px", display: "flex", alignItems: "center", gap: "8px" }}>
                        <i className="fas fa-history"></i>
                        Prescription History for {prescPatient}
                        <span style={{ color: "#888", fontSize: "0.8rem", fontWeight: "normal" }}>({patientPrescriptions.length})</span>
                      </h4>
                      <div className="elegant-scroll" style={{ maxHeight: "100px", overflowY: "auto" }}>
                        {patientPrescriptions.map(presc => (
                          <div key={presc.id} style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            padding: "8px",
                            borderBottom: "1px solid #333",
                            fontSize: "0.9rem"
                          }}>
                            <div>
                              <span style={{ color: "#fff" }}>{new Date(presc.date).toLocaleDateString()}</span>
                              {presc.diagnosis && <span style={{ color: "#888", marginLeft: "10px" }}>{presc.diagnosis.slice(0, 50)}...</span>}
                            </div>
                            <div style={{ display: "flex", gap: "8px" }}>
                              <button
                                onClick={() => downloadPrescription(presc.id, prescPatient, true)}
                                style={{ background: "#f0b800", border: "none", color: "#000", padding: "4px 10px", borderRadius: "4px", cursor: "pointer", fontSize: "0.80rem", fontWeight: "bold" }}
                                title="Download Stamped"
                              >
                                <i className="fas fa-stamp"></i> Stamped
                              </button>
                              <button
                                onClick={() => downloadPrescription(presc.id, prescPatient, false)}
                                style={{ background: "transparent", border: "1px solid #555", color: "#888", padding: "4px 10px", borderRadius: "4px", cursor: "pointer", fontSize: "0.80rem" }}
                                title="Download Plain"
                              >
                                Plain
                              </button>
                              <button
                                onClick={() => deletePrescription(presc.id)}
                                style={{ background: "transparent", border: "1px solid #e74c3c", color: "#e74c3c", padding: "4px 10px", borderRadius: "4px", cursor: "pointer", fontSize: "0.80rem" }}
                                title="Delete Prescription"
                              >
                                <i className="fas fa-trash-alt"></i>
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* ROW 5: BILLING & INVOICES */}
            <div className="row-billing" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
              <div className="card animate-fade-up" style={{ animationDelay: "0.6s", width: "100%", maxWidth: "1020px" }}>
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
                  onPatientChange={(name) => setInvoicePatient(name)}
                />

                {/* Recent Invoices for selected patient */}
                {invoicePatient && (
                  <div style={{ marginTop: "2rem", borderTop: "1px solid #333", paddingTop: "1rem" }}>
                    <h4 style={{ marginBottom: "1rem", color: "#f0b800" }}>
                      Invoices for {invoicePatient}
                    </h4>
                    <div className="elegant-scroll" style={{ maxHeight: "300px", overflowY: "auto" }}>
                      {invoices
                        .filter(inv => (inv.patient_name || "").toLowerCase() === invoicePatient.toLowerCase())
                        .length > 0 ? (
                        invoices
                          .filter(inv => (inv.patient_name || "").toLowerCase() === invoicePatient.toLowerCase())
                          .map(inv => (
                            <div key={inv.id} style={{
                              background: "#222", padding: "10px", borderRadius: "8px", marginBottom: "10px",
                              display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid #333"
                            }}>
                              <div>
                                <b style={{ color: "#fff" }}>{inv.patient_name}</b>
                                <div style={{ fontSize: "0.8rem", color: "#888" }}>{new Date(inv.date).toLocaleDateString()}</div>
                                <div style={{ fontSize: "0.85rem", color: "#2ecc71", fontWeight: "bold" }}>₹ {inv.total?.toLocaleString("en-IN")} ({inv.invoice_number})</div>
                              </div>
                              <div style={{ display: "flex", gap: "8px" }}>
                                <button
                                  onClick={() => setEditingInvoice(inv)}
                                  style={{ background: "#2ecc71", border: "none", color: "#000", padding: "5px 10px", borderRadius: "4px", fontSize: "0.80rem", cursor: "pointer", fontWeight: "bold" }}
                                >
                                  <i className="fas fa-edit"></i> Edit
                                </button>
                                <button
                                  onClick={() => downloadInvoice(inv.id, inv.invoice_number, true, inv.patient_name)}
                                  style={{ background: "#f0b800", border: "none", color: "#000", padding: "5px 10px", borderRadius: "4px", fontSize: "0.80rem", cursor: "pointer", fontWeight: "bold" }}
                                >
                                  <i className="fas fa-stamp"></i> Stamped
                                </button>
                                <button
                                  onClick={() => downloadInvoice(inv.id, inv.invoice_number, false, inv.patient_name)}
                                  style={{ background: "transparent", border: "1px solid #555", color: "#888", padding: "5px 10px", borderRadius: "4px", fontSize: "0.80rem", cursor: "pointer" }}
                                >
                                  Plain
                                </button>
                                <button
                                  onClick={() => deleteInvoice(inv.id)}
                                  style={{ background: "transparent", border: "1px solid #e74c3c", color: "#e74c3c", padding: "5px 10px", borderRadius: "4px", fontSize: "0.80rem", cursor: "pointer" }}
                                  title="Delete Invoice"
                                >
                                  <i className="fas fa-trash-alt"></i>
                                </button>
                              </div>
                            </div>
                          ))
                      ) : (
                        <p style={{ color: "#888", textAlign: "center", padding: "2rem" }}>
                          <i className="fas fa-info-circle" style={{ marginRight: "8px" }}></i>
                          No invoices found for {invoicePatient}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* ROW 6: ALL PATIENTS TABLE */}
            <div className="row-patients" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
              <div className="card animate-fade-up" style={{ animationDelay: "0.7s", width: "100%", maxWidth: "1100px" }}>
                <div className="card-header">
                  <h3>All Registered Patients</h3>
                  <i className="fas fa-users card-icon"></i>
                </div>
                <div className="elegant-scroll" style={{ padding: "1rem", overflowX: "auto", maxHeight: "400px", overflowY: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", color: "#fff", textAlign: "left" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid #333" }}>
                        <th style={{ padding: "8px 10px", color: "#f0b800", fontSize: "0.85rem" }}>Name</th>
                        <th style={{ padding: "8px 10px", color: "#f0b800", fontSize: "0.85rem" }}>Age/Sex</th>
                        <th style={{ padding: "8px 10px", color: "#f0b800", fontSize: "0.85rem" }}>Phone</th>
                        <th style={{ padding: "8px 10px", color: "#f0b800", fontSize: "0.85rem" }}>Email</th>
                        <th style={{ padding: "8px 10px", color: "#f0b800", fontSize: "0.85rem" }}>Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {patientsList.length > 0 ? (
                        patientsList.map(p => (
                          <tr key={p.id} style={{ borderBottom: "1px solid #222" }}>
                            <td style={{ padding: "8px 10px", fontSize: "0.9rem" }}>{p.name}</td>
                            <td style={{ padding: "8px 10px", color: "#ddd", fontSize: "0.85rem" }}>{p.age || "-"} / {p.sex || p.gender || "-"}</td>
                            <td style={{ padding: "8px 10px", color: "#888", fontSize: "0.85rem" }}>{(!p.phone || p.phone.startsWith("TEMP_")) ? "N/A" : p.phone}</td>
                            <td style={{ padding: "8px 10px", color: "#888", fontSize: "0.85rem" }}>{p.email || "-"}</td>
                            <td style={{ padding: "8px 10px" }}>
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
                          <td colSpan="5" style={{ textAlign: "center", padding: "2rem", color: "#888" }}>No patients found.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

          </div>
        </main>

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
                  Hi <b>Dr. {user.firstName}</b>! How can FlossyAI assist you today?
                </p>
                <div className="ai-chips">
                  <button onClick={() => sendAiMessage("Summarize today's appointments")}>📅 Today's Schedule</button>
                  <button onClick={() => sendAiMessage("Patient follow-up reminders")}>🔔 Follow-ups</button>
                  <button onClick={() => sendAiMessage("Generate a prescription template")}>💊 Prescription</button>
                  <button onClick={() => sendAiMessage("Analyze patient risk profiles")}>📊 Risk Analysis</button>
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={m.from === "ai" ? "msg-ai" : "msg-user"}>
                <b>{m.from === "ai" ? "FlossyAI" : "You"}:</b> {m.text}
              </div>
            ))}
            {typing && <div className="typing">FlossyAI is typing<span className="dot-one">.</span><span className="dot-two">.</span><span className="dot-three">.</span></div>}
            <div ref={messagesEndRef} />
          </div>

          <div className="ai-input-area">
            <input
              type="text"
              placeholder="Ask something..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendAiMessage()}
            />
            <button onClick={() => sendAiMessage()}>Send</button>
          </div>
        </aside>

        <Footer />
      </div>
    </div>
  );
}
