import { useEffect, useState } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { PropagateLoader } from "react-spinners";

import Header from "./DashboardHeader";
import Footer from "../../components/Footer";
import InvoiceForm from "../../components/InvoiceForm";

import { TIME_SLOTS, formatTime12h } from "../../utils/timeSlots";

import "../../styles/dentist_dashboard.css";
import "../../styles/dashboard_extras.css";
import "../../styles/patient_dashboard.css";

/* ==============================
   CONFIG
================================ */

const API = import.meta.env.VITE_API_BASE_URL?.replace(
  "http://",
  "https://"
);

/* ==============================
   MEDICATION CONSTANTS
================================ */

const DENTAL_MEDICATIONS = [
  { name: "Amoxicillin 500mg", type: "Antibiotic" },
  { name: "Augmentin 625mg", type: "Antibiotic" },
  { name: "Metronidazole 400mg", type: "Antibiotic" },
  { name: "Clindamycin 300mg", type: "Antibiotic" },
  { name: "Azithromycin 500mg", type: "Antibiotic" },

  { name: "Ibuprofen 400mg", type: "Pain Relief" },
  { name: "Paracetamol 650mg", type: "Pain Relief" },

  { name: "Pantoprazole 40mg", type: "Antacid" },

  { name: "Chlorhexidine Mouthwash", type: "Mouthwash" },
  { name: "Hexigel", type: "Topical" }
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
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [profileVisible, setProfileVisible] = useState(true);

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
  const [prescMedSearch, setPrescMedSearch] = useState("");

  // ===== ANALYTICS STATE =====
  const [reportDate, setReportDate] = useState(new Date().toISOString().split('T')[0]);
  const [reportView, setReportView] = useState("daily");

  // ===== HISTORY FILTER STATE =====
  const [historyNameFilter, setHistoryNameFilter] = useState("");
  const [historyDateFilter, setHistoryDateFilter] = useState("");

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

    // Set page title
    document.title = `Dr. ${user.firstName || 'Dentist'} | Dentist Dashboard - Smile Artists`;
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
    const res = await fetch(`${API}/api/patients/?role=patient`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      // Filter only patients (not doctors/receptionists)
      const onlyPatients = data.filter(p => p.role === 'patient' || !p.role);
      setPatientsList(onlyPatients);
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
          diagnosis: prescNotes,
          treatment_plan: prescTreatmentPlan,
          recommendations: prescRecommendations,
          medications: prescMedications.filter(m => m.name),
          doctor_name: fullName
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
        setPrescMedSearch("");
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

  async function downloadPrescription(id, patientName = "") {
    const token = await session.getToken({ template: "default" });
    const res = await fetch(`${API}/api/prescriptions/${id}/pdf`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const safeName = patientName ? patientName.replace(/[^a-zA-Z0-9]/g, "_") : "patient";
      a.download = `${safeName}_prescription.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
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
    <div className={`dashboard-shell ${!profileVisible ? "sidebar-collapsed" : "sidebar-expanded"}`}>
      {/* DOCTOR PROFILE SIDEBAR */}
      <aside className="profile-sidebar">
        {/* Toggle button */}
        <div
          className="sidebar-expand-toggle"
          onClick={() => setProfileVisible(!profileVisible)}
          title={profileVisible ? "Hide Sidebar" : "Show Sidebar"}
        >
          <i className={`fas fa-${profileVisible ? 'chevron-left' : 'bars'}`}></i>
        </div>

        {/* Close button - only when expanded */}
        {profileVisible && (
          <button
            className="sidebar-close-btn"
            onClick={() => setProfileVisible(false)}
            title="Close Sidebar"
            style={{ top: '5.5rem' }}
          >
            <i className="fas fa-times"></i>
          </button>
        )}

        <div className="profile-sidebar-content">
          <div className="profile-avatar">
            {user?.imageUrl ? (
              <img src={user.imageUrl} alt="Profile" />
            ) : (
              <div className="avatar-placeholder">
                <i className="fas fa-user-md"></i>
              </div>
            )}
          </div>

          <div className="profile-header-text">
            <h3 className="profile-name">Dr. {fullName}</h3>
            <span className="profile-role">Dentist</span>
          </div>

          <div className="profile-info-grid" style={{ justifyContent: 'center', textAlign: 'center' }}>
            <div className="profile-stat">
              <span className="stat-value">{today.length}</span>
              <span className="stat-label">Today</span>
            </div>
            <div className="profile-stat">
              <span className="stat-value">{upcoming.length}</span>
              <span className="stat-label">Upcoming</span>
            </div>
            <div className="profile-stat">
              <span className="stat-value">{history.length}</span>
              <span className="stat-label">History</span>
            </div>
          </div>

          <div className="profile-details-compact">
            <div className="detail-row" title={user?.primaryEmailAddress?.emailAddress}>
              <i className="fas fa-envelope"></i>
              <span>{user?.primaryEmailAddress?.emailAddress || "No email"}</span>
            </div>
            <div className="detail-row">
              <i className="fas fa-stethoscope"></i>
              <span>General Dentistry</span>
            </div>
            <div className="detail-row">
              <i className="fas fa-clinic-medical"></i>
              <span>Smile Artists Dental Studio</span>
            </div>
          </div>

          <div className="sidebar-actions">
            <button className="p-btn sidebar-book-btn" onClick={() => setAiOpen(true)}>
              <i className="fas fa-robot"></i> <span>FlossyAI</span>
            </button>
          </div>
        </div>
      </aside>

      <div className="dashboard-main-content">
        <Header openAI={() => setAiOpen(true)} />

        <main className="dentist-main">
          <h2 id="Message">Welcome back, Dr. {fullName}</h2>

          <div className="dashboard-layout" style={{ display: "flex", flexDirection: "column", gap: "2rem", paddingBottom: "3rem" }}>

            {/* ROW 1: APPOINTMENTS (SIDE BY SIDE) */}
            <div className="row-appointments" style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "1.5rem" }}>

              {/* TODAY */}
              <div className="card animate-fade-up" style={{ animationDelay: "0.1s", flex: "1", minWidth: "350px", maxWidth: "500px" }}>
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
                      <div className="appt-patient">{a.patient}</div>
                      <div className="appt-reason">{a.reason}</div>
                    </div>
                  ))
                ) : (
                  <p style={{ color: "#888", fontStyle: "italic" }}>No appointments today</p>
                )}
              </div>

              {/* UPCOMING */}
              <div className="card animate-fade-up" style={{ animationDelay: "0.2s", flex: "1", minWidth: "350px", maxWidth: "500px" }}>
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
                      <div className="appt-patient">{a.patient}</div>
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
                    <input
                      type="text"
                      placeholder="Patient name..."
                      value={historyNameFilter}
                      onChange={(e) => setHistoryNameFilter(e.target.value)}
                      style={{ width: "100%", padding: "10px", background: "#222", border: "1px solid #333", borderRadius: "5px", color: "#fff" }}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: "200px" }}>
                    <label style={{ color: "#888", fontSize: "0.8rem", display: "block", marginBottom: "5px" }}>Filter by Date</label>
                    <input
                      type="date"
                      value={historyDateFilter}
                      onChange={(e) => setHistoryDateFilter(e.target.value)}
                      style={{ width: "100%", padding: "10px", background: "#222", border: "1px solid #333", borderRadius: "5px", color: "#fff", colorScheme: "dark" }}
                    />
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
                  <p style={{ color: "#888", fontStyle: "italic", padding: "1rem" }}>No past appointments</p>
                )}
              </div>
            </div>

            {/* ROW 3: DAILY ANALYTICS */}
            <div className="row-stats" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
              <div className="card animate-fade-up" style={{ animationDelay: "0.4s", width: "100%", maxWidth: "1020px" }}>
                <div className="card-header">
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <h3>Daily Analytics</h3>
                    <input
                      type="date"
                      value={reportDate}
                      onChange={(e) => setReportDate(e.target.value)}
                      style={{
                        background: "rgba(0,0,0,0.3)",
                        border: "1px solid #555",
                        color: "#fff",
                        padding: "5px 10px",
                        borderRadius: "5px",
                        fontSize: "0.9rem",
                        cursor: "pointer",
                        colorScheme: "dark"
                      }}
                    />
                    <select
                      value={reportView}
                      onChange={(e) => setReportView(e.target.value)}
                      style={{
                        background: "rgba(0,0,0,0.3)",
                        border: "1px solid #555",
                        color: "#fff",
                        padding: "5px 10px",
                        borderRadius: "5px",
                        fontSize: "0.9rem",
                        cursor: "pointer",
                        colorScheme: "dark"
                      }}
                    >
                      <option value="daily">Daily</option>
                      <option value="monthly">Monthly</option>
                      <option value="yearly">Yearly</option>
                    </select>
                  </div>
                  <i className="fas fa-chart-line card-icon"></i>
                </div>
                <div style={{ padding: "1rem" }}>
                  {/* METRICS CARDS */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
                    <div style={{ background: "#222", padding: "1.5rem", borderRadius: "10px", textAlign: "center", border: "1px solid #333" }}>
                      <h4 style={{ color: "#888", marginBottom: "0.5rem" }}>Appointments Done</h4>
                      <div style={{ fontSize: "2rem", color: "#2ecc71", fontWeight: "bold" }}>
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
                    <div style={{ background: "#222", padding: "1.5rem", borderRadius: "10px", textAlign: "center", border: "1px solid #333" }}>
                      <h4 style={{ color: "#888", marginBottom: "0.5rem" }}>Revenue Generated</h4>
                      <div style={{ fontSize: "2rem", color: "#f0b800", fontWeight: "bold" }}>
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
                          .toLocaleString()}
                      </div>
                    </div>
                    <div style={{ background: "#222", padding: "1.5rem", borderRadius: "10px", textAlign: "center", border: "1px solid #333" }}>
                      <h4 style={{ color: "#888", marginBottom: "0.5rem" }}>Total Patients</h4>
                      <div style={{ fontSize: "2rem", color: "#3498db", fontWeight: "bold" }}>
                        {patientsList.length}
                      </div>
                    </div>
                    <div style={{ background: "#222", padding: "1.5rem", borderRadius: "10px", textAlign: "center", border: "1px solid #333" }}>
                      <h4 style={{ color: "#888", marginBottom: "0.5rem" }}>Prescriptions Written</h4>
                      <div style={{ fontSize: "2rem", color: "#9b59b6", fontWeight: "bold" }}>
                        {recentPrescriptions.length}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* ROW 4: PRESCRIPTIONS */}
            <div className="row-prescriptions" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
              <div className="card animate-fade-up" style={{ animationDelay: "0.5s", width: "100%", maxWidth: "1020px", background: "#1a1a1a", borderRadius: "10px", border: "1px solid #333" }}>
                <div style={{ padding: "1.5rem" }}>

                  {/* SELECT PATIENT */}
                  <div style={{ marginBottom: "1.5rem" }}>
                    <label style={{ color: "#f0b800", fontWeight: "bold", marginBottom: "10px", display: "block", textTransform: "uppercase", letterSpacing: "1px" }}>Select Patient</label>
                    <select
                      value={prescPatient}
                      onChange={(e) => {
                        setPrescPatient(e.target.value);
                        fetchPatientPrescriptions(e.target.value);
                      }}
                      style={{
                        width: "100%",
                        padding: "15px",
                        background: "#222",
                        border: "1px solid #444",
                        borderRadius: "8px",
                        color: "#fff",
                        fontSize: "1rem",
                        cursor: "pointer"
                      }}
                    >
                      <option value="">-- Choose Patient --</option>
                      {patientsList.map(p => (
                        <option key={p.id} value={p.name}>{p.name}</option>
                      ))}
                    </select>
                  </div>

                  {/* PATIENT PRESCRIPTION HISTORY */}
                  {prescPatient && patientPrescriptions.length > 0 && (
                    <div style={{ marginBottom: "1.5rem", background: "#222", borderRadius: "8px", border: "1px solid #444", padding: "1rem" }}>
                      <h4 style={{ color: "#f0b800", marginBottom: "10px" }}>
                        <i className="fas fa-history" style={{ marginRight: "8px" }}></i>
                        Prescription History for {prescPatient}
                      </h4>
                      <div style={{ maxHeight: "150px", overflowY: "auto" }} className="elegant-scroll">
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
                            <button
                              onClick={() => downloadPrescription(presc.id, prescPatient)}
                              style={{ background: "#333", border: "none", color: "#f0b800", padding: "4px 10px", borderRadius: "4px", cursor: "pointer", fontSize: "0.8rem" }}
                            >
                              <i className="fas fa-download"></i>
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* DIAGNOSIS & TREATMENT PLAN - Side by Side */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
                    <div>
                      <label style={{ color: "#fff", fontWeight: "bold", marginBottom: "10px", display: "block", textTransform: "uppercase", letterSpacing: "1px" }}>Diagnosis</label>
                      <textarea
                        placeholder="e.g. Chronic Gingivitis..."
                        value={prescNotes}
                        onChange={(e) => setPrescNotes(e.target.value)}
                        style={{
                          width: "100%",
                          padding: "15px",
                          background: "#222",
                          border: "1px solid #444",
                          borderRadius: "8px",
                          color: "#fff",
                          fontSize: "0.95rem",
                          minHeight: "120px",
                          resize: "vertical"
                        }}
                      ></textarea>
                    </div>
                    <div>
                      <label style={{ color: "#fff", fontWeight: "bold", marginBottom: "10px", display: "block", textTransform: "uppercase", letterSpacing: "1px" }}>Treatment Plan</label>
                      <textarea
                        placeholder="e.g. Scaling and Root Planing..."
                        value={prescTreatmentPlan || ""}
                        onChange={(e) => setPrescTreatmentPlan(e.target.value)}
                        style={{
                          width: "100%",
                          padding: "15px",
                          background: "#222",
                          border: "1px solid #444",
                          borderRadius: "8px",
                          color: "#fff",
                          fontSize: "0.95rem",
                          minHeight: "120px",
                          resize: "vertical"
                        }}
                      ></textarea>
                    </div>
                  </div>

                  {/* RECOMMENDATIONS / MEDICATIONS */}
                  <div style={{ marginBottom: "1.5rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                      <label style={{ color: "#fff", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "1px" }}>Recommendations / Medications</label>
                      <div style={{ position: "relative", width: "250px" }}>
                        <i className="fas fa-search" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "#666" }}></i>
                        <input
                          type="text"
                          placeholder="Search medication..."
                          value={prescMedSearch || ""}
                          onChange={(e) => setPrescMedSearch(e.target.value)}
                          style={{
                            width: "100%",
                            padding: "10px 10px 10px 35px",
                            background: "#333",
                            border: "1px solid #555",
                            borderRadius: "5px",
                            color: "#fff",
                            fontSize: "0.9rem"
                          }}
                        />
                      </div>
                    </div>
                    <textarea
                      placeholder="e.g. Warm salt water rinses, twice daily..."
                      value={prescRecommendations || ""}
                      onChange={(e) => setPrescRecommendations(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "15px",
                        background: "#222",
                        border: "1px solid #444",
                        borderRadius: "8px",
                        color: "#fff",
                        fontSize: "0.95rem",
                        minHeight: "120px",
                        resize: "vertical"
                      }}
                    ></textarea>
                  </div>

                  {/* UPLOAD PRESCRIPTION BUTTON */}
                  <button
                    onClick={submitPrescription}
                    disabled={prescSubmitting || !prescPatient}
                    style={{
                      width: "100%",
                      padding: "18px",
                      background: "#f0b800",
                      color: "#000",
                      border: "none",
                      borderRadius: "0 0 10px 10px",
                      fontWeight: "bold",
                      fontSize: "1rem",
                      cursor: prescPatient ? "pointer" : "not-allowed",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "10px",
                      marginTop: "1rem",
                      marginLeft: "-1.5rem",
                      marginRight: "-1.5rem",
                      marginBottom: "-1.5rem",
                      width: "calc(100% + 3rem)"
                    }}
                  >
                    <i className="fas fa-upload"></i>
                    {prescSubmitting ? "UPLOADING..." : "UPLOAD PRESCRIPTION"}
                  </button>
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
                                <div style={{ fontSize: "0.85rem", color: "#2ecc71", fontWeight: "bold" }}>₹ {inv.total?.toLocaleString()} ({inv.invoice_number})</div>
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
                        <th style={{ padding: "12px", color: "#f0b800" }}>Name</th>
                        <th style={{ padding: "12px", color: "#f0b800" }}>Age/Sex</th>
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
                            <td style={{ padding: "12px", color: "#ddd" }}>{p.age || "-"} / {p.sex || p.gender || "-"}</td>
                            <td style={{ padding: "12px", color: "#888" }}>{(!p.phone || p.phone.startsWith("TEMP_")) ? "N/A" : p.phone}</td>
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

        <Footer />
      </div>
    </div>
  );
}
