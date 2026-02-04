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

  useEffect(() => {
    if (!isLoaded || !session) return;

    loadAppointments()
      .catch(console.error)
      .finally(() => setPageLoading(false));
  }, [isLoaded, session]);

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
                {history.length ? (
                  <div style={{ maxHeight: "300px", overflowY: "auto" }} className="elegant-scroll">
                    {history.slice(0, 10).map((a) => (
                      <div className="appt-item" key={a.id} style={{ opacity: 0.8 }}>
                        <b>
                          {new Date(a.time).toLocaleDateString()} {new Date(a.time).toLocaleTimeString("en-IN", {
                            hour: "2-digit",
                            minute: "2-digit",
                            hour12: true
                          })}
                        </b>
                        <div className="appt-patient">{a.patient}</div>
                        <div className="appt-reason">{a.reason}</div>
                        {a.completed && <span className="completed-tag">Completed</span>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: "#888", fontStyle: "italic" }}>No past appointments</p>
                )}
              </div>
            </div>

          </div>
        </main>

        <Footer />
      </div>
    </div>
  );
}
