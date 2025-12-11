import { useEffect, useState } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { PropagateLoader } from "react-spinners";
import Header from "./DashboardHeader";
import Footer from "../../components/Footer";
import "../../styles/patient_dashboard.css";

export default function PatientDashboard() {
  const { user, isLoaded } = useUser();
  const { session } = useSession();
  const navigate = useNavigate();

  const [pageLoading, setPageLoading] = useState(true);
  const [today, setToday] = useState([]);
  const [upcoming, setUpcoming] = useState([]);

  const [messages, setMessages] = useState([]);
  const [aiOpen, setAiOpen] = useState(false);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);

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

  const fullName = `${user.firstName || ""} ${user.lastName || ""}`.trim();

  return (
    <>
      <Header openAI={() => setAiOpen(true)} />

      <main className="dentist-main">
        <h2 id="welcomeMessage">Welcome back, {fullName}!</h2>

        <div className="grid">

          {/* TODAY */}
          <div className="card">
            <h3>Today’s Appointments</h3>
            {today.length ? (
              today.map((a) => (
                <div className="appt-item" key={a.id}>
                  <b>{formatApptTime(a.time)}</b>
                  <div>Doctor: {a.doctor_name}</div>
                  <div>Reason: {a.reason}</div>
                </div>
              ))
            ) : (
              <p>No appointments today.</p>
            )}
          </div>

          {/* UPCOMING */}
          <div className="card">
            <h3>Upcoming Appointments</h3>
            {upcoming.length ? (
              upcoming.map((a) => (
                <div className="appt-item" key={a.id}>
                  <b>{formatApptTime(a.time)}</b>
                  <div>Doctor: {a.doctor_name}</div>
                  <div>Reason: {a.reason}</div>
                </div>
              ))
            ) : (
              <p>No upcoming appointments.</p>
            )}
          </div>

          {/* AI CARE INSIGHTS */}
          <div className="card">
            <h3>AI Care Insights</h3>
            <p>Your teeth & gums look great this month! 🦷✨</p>
          </div>

          {/* NOTIFICATIONS */}
          <div className="card">
            <h3>Notifications</h3>
            <p>You have no new notifications.</p>
          </div>

        </div>
      </main>

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
