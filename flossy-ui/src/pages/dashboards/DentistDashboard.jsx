import { useEffect, useState } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { PropagateLoader } from "react-spinners";
import Header from "./DashboardHeader";
import Footer from "../../components/Footer";
import "../../styles/dentist_dashboard.css";

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

  const API = "http://localhost:8000";

  // === Fetch Appointments ===
  async function loadAppointments() {
    const token = await session.getToken({ template: "default"});
    const res = await fetch(`${API}/api/appointments/dentist_upcoming`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    const data = await res.json();
    setToday(data.today || []);
    setUpcoming(data.upcoming || []);
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
  

  function capitalizeFullName(name) {
    if (!name) return "";
    return name
      .trim()
      .split(/\s+/)
      .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(" ");
  }
  

  // === AI Chat ===
  async function sendMessage() {
    if (!input.trim()) return;

    const text = input;
    setInput("");
    setMessages((prev) => [...prev, { from: "user", text }]);

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
          <div className="card">
            <h3>Today’s Appointments</h3>
            {today.length ? (
              today.map((a) => (
                <div className="appt-item" key={a.id}>
                  <b>
                    {new Date(a.time).toLocaleDateString("en-IN", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric"
                    })}{" "}
                    •{" "}
                    {new Date(a.time)
                      .toLocaleTimeString("en-IN", {
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: true
                      })
                      .replace("am", "AM")
                      .replace("pm", "PM")}
                  </b>
                  <div>{capitalizeFullName(a.patient_name)}</div>
                  <div>Reason: {a.reason}</div>
                  <div>Phone: {a.phone}</div>
                  {/* 🔥 Mark Completed button */}
                  {a.status !== "completed" && (
                    <button className="done-btn" onClick={() => markCompleted(a.id)}>
                      Mark Completed
                    </button>
                  )}

                  {a.status === "completed" && (
                    <span className="completed-tag">Completed ✔</span>
                  )}
                </div>
              ))
            ) : (
              <p>No appointments today.</p>
            )}
          </div>

          <div className="card">
            <h3>Recent Interactions</h3>
            <p>Loading...</p>
          </div>

          <div className="card">
            <h3>AI Insights</h3>
            <p>FlossyAI detected gum disease risk this week.</p>
          </div>

          <div className="card">
            <h3>Notifications</h3>
            <p>2 new appointment requests.</p>
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
        </div>

        <div className="ai-input-area">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask FlossyAI..."
          />
          <button onClick={sendMessage}>Send</button>
        </div>
      </div>

      <Footer />
    </>
  );
}
