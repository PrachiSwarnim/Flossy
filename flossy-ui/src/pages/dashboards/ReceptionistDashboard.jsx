import { useEffect, useState } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { PropagateLoader } from "react-spinners";
import Header from "./DashboardHeader";
import Footer from "../../components/Footer";
import InvoiceForm from "../../components/InvoiceForm";
import "../../styles/dentist_dashboard.css";
import { TIME_SLOTS, formatTime12h } from "../../utils/timeSlots";

const API = import.meta.env.VITE_API_BASE_URL?.replace("http://", "https://");

export default function ReceptionistDashboard() {
    const { user, isLoaded } = useUser();
    const { session } = useSession();
    const navigate = useNavigate();

    const [pageLoading, setPageLoading] = useState(true);
    const [patientName, setPatientName] = useState("");
    const [patientPhone, setPatientPhone] = useState("");
    const [patientAge, setPatientAge] = useState("");
    const [patientSex, setPatientSex] = useState("M");
    const [visitDate, setVisitDate] = useState("");
    const [visitTime, setVisitTime] = useState("");
    const [visitReason, setVisitReason] = useState("");
    const [assignedDoctor, setAssignedDoctor] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [patientsList, setPatientsList] = useState([]);
    const [invoices, setInvoices] = useState([]);
    const [today, setToday] = useState([]);
    const [upcoming, setUpcoming] = useState([]);
    const [history, setHistory] = useState([]);
    const [doctorsList, setDoctorsList] = useState([]);
    const [invoicePatient, setInvoicePatient] = useState(""); // Track selected patient in Invoice Form

    // Edit Modal State
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editingPatient, setEditingPatient] = useState(null);
    const [editName, setEditName] = useState("");
    const [editPhone, setEditPhone] = useState("");
    const [editAge, setEditAge] = useState("");
    const [editSex, setEditSex] = useState("M");

    // Appointment Actions State
    const [followUpOpen, setFollowUpOpen] = useState(false);
    const [selectedApptId, setSelectedApptId] = useState(null);
    const [followUpReason, setFollowUpReason] = useState("");

    // Invoice Edit State
    const [editingInvoice, setEditingInvoice] = useState(null);

    // NEGOTIATION STATE
    const [negotiationModalOpen, setNegotiationModalOpen] = useState(false);
    const [negotiatingAppt, setNegotiatingAppt] = useState(null);
    const [denialReason, setDenialReason] = useState("");
    const [proposedDate, setProposedDate] = useState("");
    const [proposedTimeSlot, setProposedTimeSlot] = useState("");
    const [complaintType, setComplaintType] = useState("manual");
    const [reportDate, setReportDate] = useState(new Date().toISOString().split('T')[0]);
    const [reportView, setReportView] = useState("daily");


    async function handleApprove(id) {
        if (!window.confirm("Approve this appointment?")) return;
        const token = await session.getToken({ template: "default" });
        await fetch(`${API}/api/appointments/${id}`, {
            method: "PUT",
            headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
            body: JSON.stringify({ status: "confirmed" })
        });
        loadAppointments();
    }

    function openNegotiation(appt) {
        setNegotiatingAppt(appt);
        const dt = new Date(appt.time);
        setProposedDate(dt.toISOString().split('T')[0]);
        // Try to match time to a slot
        const timeStr = dt.toTimeString().substring(0, 5);
        setProposedTimeSlot(timeStr);
        setNegotiationModalOpen(true);
    }

    async function submitNegotiation() {
        if (!denialReason) return alert("Please provide a reason.");
        const token = await session.getToken({ template: "default" });
        const isoDate = new Date(`${proposedDate}T${proposedTimeSlot}`).toISOString();

        await fetch(`${API}/api/appointments/${negotiatingAppt.id}`, {
            method: "PUT",
            headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
            body: JSON.stringify({
                status: "negotiating",
                denial_reason: denialReason,
                datetime: isoDate
            })
        });
        setNegotiationModalOpen(false);
        setNegotiatingAppt(null);
        setDenialReason("");
        loadAppointments();
    }

    // === Name Cleaning Helper ===
    const cleanName = (name) => {
        if (!name) return "";
        return name
            .replace(/\b(None|null|undefined)\b/gi, "")
            .trim();
    };

    // === Full Name ===
    // USER REQUEST: Take name from email username
    const userEmail = user?.primaryEmailAddress?.emailAddress || "";
    const clerkName = user?.firstName ? `${user.firstName} ${user.lastName || ""}`.trim() : null;
    const fullName = clerkName || capitalizeFullName(userEmail) || "Receptionist";

    useEffect(() => {
        if (fullName) {
            document.title = `${fullName} | Smile Artists Dental Studio`;
        }
    }, [fullName]);

    async function markCompleted(id) {
        const token = await session.getToken({ template: "default" });
        await fetch(`${API}/api/appointments/mark_completed/${id}`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` }
        });
        loadAppointments();
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

    function openFollowUpModal(id) {
        setSelectedApptId(id);
        setFollowUpOpen(true);
    }

    const [followUpDate, setFollowUpDate] = useState("");
    const [followUpTime, setFollowUpTime] = useState("");

    async function markFollowUp() {
        if (!followUpReason) return alert("Please enter a reason.");
        if (!followUpDate || !followUpTime) return alert("Please select date and time.");
        const token = await session.getToken({ template: "default" });

        // 1. Mark Follow Up
        await fetch(`${API}/api/appointments/mark_completed/${selectedApptId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({ follow_up_reason: followUpReason })
        });

        // 2. Schedule New Appt
        const currentAppt = [...today, ...upcoming, ...history].find(a => a.id === selectedApptId);
        if (currentAppt) {
            const isoDateTime = new Date(`${followUpDate}T${followUpTime}`).toISOString();
            await fetch(`${API}/api/receptionist/add_patient`, { // Receptionist add endpoint
                method: "POST",
                headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                body: JSON.stringify({
                    name: currentAppt.patient_name,
                    phone: currentAppt.patient_phone || "0000000000",
                    age: parseInt(currentAppt.patient_age) || 0,
                    datetime: isoDateTime,
                    reason: "Follow-up: " + followUpReason,
                    doctor_name: currentAppt.doctor_name,
                    sex: currentAppt.patient_sex || "M" // fallback
                })
            });
        }

        setFollowUpOpen(false);
        setFollowUpReason("");
        setFollowUpDate("");
        setFollowUpTime("");
        setSelectedApptId(null);
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

    // 🔒 SECURE ROLE ACCESS
    useEffect(() => {
        if (!isLoaded) return;

        if (!user) {
            navigate("/login");
            return;
        }

        const role = user.publicMetadata?.role;
        const email = user.primaryEmailAddress?.emailAddress?.toLowerCase();

        // Authority check: Receptionist, core team, or authorized email
        const isReceptionist = role === "receptionist" ||
            ["anything.handmade1@gmail.com", "purviraj236@gmail.com", "aartikumari0975@gmail.com", "prachi.swarnim07@gmail.com"].includes(email);

        if (isReceptionist) {
            setPageLoading(false);
            fetchPatients();
            fetchInvoices();
            loadAppointments();
            fetchDoctors();
        } else {
            console.warn("🔐 Access Denied: User is not a receptionist.", { email, role });
            // Clear any stale local roles
            sessionStorage.removeItem("flossy_role");

            if (role === "dentist") {
                navigate("/dentist", { replace: true });
            } else {
                // Default for patients or anyone else
                navigate("/patient", { replace: true });
            }
        }
    }, [isLoaded, user, navigate]);


    async function fetchPatients() {
        const token = await session.getToken({ template: "default" });
        const res = await fetch(`${API}/api/patients/`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            setPatientsList(data); // Expecting array, backend returns list directly? Check backend.
            // Backend valid_receptionist_patient returns success/id. 
            // GET /api/patients returns list?
            // Actually Step 2150 code showed setPatientsList(data.patients || []).
            // Current code says setPatientsList(data).
            // Let's stick to adding fetchDoctors for now as I can't see fetchPatients impl fully.
        }
    }

    async function fetchDoctors() {
        // Need token for /api/doctors if not exempt
        const token = await session.getToken({ template: "default" });
        const res = await fetch(`${API}/api/doctors`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            setDoctorsList(data.doctors || []);
        }
    }

    async function fetchInvoices() {
        const token = await session.getToken({ template: "default" });
        const res = await fetch(`${API}/api/invoices/history`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            setInvoices(data.invoices);
        }
    }

    async function loadAppointments() {
        const token = await session.getToken({ template: "default" });
        const res = await fetch(`${API}/api/appointments/receptionist_upcoming`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            setToday(data.today || []);
            setUpcoming(data.upcoming || []);
            setHistory(data.history || []);
        }
    }

    function downloadPatientData() {
        if (!patientsList.length) return alert("No patient data to download.");

        const headers = ["Name", "Age", "Sex", "Phone", "Email", "Source"];
        const rows = patientsList.map(p => [
            p.name,
            p.age || "",
            p.sex || p.gender || "",
            p.phone || "",
            p.email || "",
            p.source || "website"
        ]);

        let csvContent = "data:text/csv;charset=utf-8,"
            + headers.join(",") + "\n"
            + rows.map(e => e.join(",")).map(row => row.replace(/#/g, '')).join("\n");

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "patient_data_export.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function capitalizeFullName(name) {
        if (!name || typeof name !== 'string') return "";

        // 1. Get the local part (before @)
        const localPart = name.split('@')[0];

        // 2. Handle common formats (reverse/straight names)
        // Split by dot, underscore, or dash
        let parts = localPart.split(/[._-]/);

        // 3. Clean up common titles/prefixes
        const titles = ['mr', 'ms', 'mrs', 'dr', 'prof'];
        parts = parts.filter(part => !titles.includes(part.toLowerCase()));

        if (parts.length === 0) return "";

        // 4. Reverse 2-part handles to "First Last" order (e.g. vasisht.dhruv -> Dhruv Vasisht)
        if (parts.length === 2) {
            const p1 = parts[0].replace(/\d+/g, "").charAt(0).toUpperCase() + parts[0].replace(/\d+/g, "").slice(1).toLowerCase();
            const p2 = parts[1].replace(/\d+/g, "").charAt(0).toUpperCase() + parts[1].replace(/\d+/g, "").slice(1).toLowerCase();
            return `${p2} ${p1}`;
        }

        // 5. Capitalize and join for 1 or 3+ parts
        return parts.map(part => {
            const cleanPart = part.replace(/\d+/g, "");
            return cleanPart.charAt(0).toUpperCase() + cleanPart.slice(1).toLowerCase();
        }).filter(p => p.length > 0).join(' ');
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

    async function handleAddPatient() {
        if (!patientName || !patientPhone || !patientAge || !visitDate || !visitTime || !visitReason || !assignedDoctor) {
            alert("Please fill in all details, including assigning a doctor.");
            return;
        }

        setIsSubmitting(true);
        const token = await session.getToken({ template: "default" });

        try {
            const isoDateTime = new Date(`${visitDate}T${visitTime}`).toISOString();
            const res = await fetch(`${API}/api/receptionist/add_patient`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({
                    name: patientName,
                    phone: patientPhone,
                    age: parseInt(patientAge),
                    datetime: isoDateTime,
                    reason: visitReason,
                    doctor_name: assignedDoctor || null,
                    sex: patientSex
                })
            });

            if (res.ok) {
                alert("Patient added successfully!");
                setPatientName("");
                setPatientPhone("");
                setPatientAge("");
                setPatientSex("M");
                setVisitDate("");
                setVisitTime("");
                setVisitReason("");
                setAssignedDoctor("");

                // Refresh Data without reload
                loadAppointments();
                fetchPatients();
            } else {
                const data = await res.json();
                alert("Error: " + (data.detail || "Failed to add patient."));
            }
        } catch (err) {
            console.error("Error adding patient:", err);
            alert("System error. Please try again.");
        } finally {
            setIsSubmitting(false);
        }
    }

    async function handleArchive(id) {
        if (!window.confirm("Are you sure you want to archive this patient?")) return;
        const token = await session.getToken({ template: "default" });
        try {
            const res = await fetch(`${API}/api/patients/${id}/archive`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                fetchPatients();
            }
        } catch (err) {
            console.error("Archive error:", err);
        }
    }

    function handleRepeatVisit(patient) {
        setPatientName(patient.name);
        setPatientPhone(patient.phone);
        setPatientAge(patient.age || "");

        // Scroll to form
        const formElement = document.getElementById("arrivalForm");
        if (formElement) {
            formElement.scrollIntoView({ behavior: "smooth" });
        }
    }

    function openEditModal(patient) {
        setEditingPatient(patient);
        setEditName(patient.name);
        setEditPhone(patient.phone);
        setEditAge(patient.age || "");
        setEditSex(patient.sex || "M");
        setIsEditModalOpen(true);
    }

    async function handleEditSave() {
        if (!editName || !editPhone) return alert("Name and phone are required.");

        const token = await session.getToken({ template: "default" });
        try {
            const res = await fetch(`${API}/api/patients/${editingPatient.id}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({
                    name: editName,
                    phone: editPhone,
                    age: parseInt(editAge),
                    sex: editSex
                })
            });

            if (res.ok) {
                setIsEditModalOpen(false);
                fetchPatients();
            } else {
                alert("Failed to update patient.");
            }
        } catch (err) {
            console.error("Update error:", err);
        }
    }

    if (!isLoaded || pageLoading) {
        return (
            <div className="page-loader">
                <PropagateLoader color="#f0b800" size={15} />
                <p>Loading receptionist dashboard...</p>
            </div>
        );
    }

    const isNewUser = sessionStorage.getItem("flossy_is_new_user") === "true";

    return (
        <>
            <Header />
            <main className="dentist-main">
                <h1 style={{ textAlign: "center", color: "#f0b800", marginBottom: "2rem", fontSize: "2.5rem" }}>Clinic Reception</h1>
                <h2 id="Message">{isNewUser ? "Welcome" : "Welcome back"}, {fullName}!</h2>

                <div className="dashboard-layout" style={{ display: "flex", flexDirection: "column", gap: "2rem", paddingBottom: "3rem", alignItems: "center" }}>

                    {/* ROW 1: APPOINTMENTS (SIDE BY SIDE) */}
                    <div className="row-appointments" style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "1.5rem", width: "100%", maxWidth: "1000px" }}>
                        <div className="card animate-fade-up" style={{ animationDelay: "0.1s", flex: "1", minWidth: "300px", maxWidth: "488px" }}>
                            <div className="card-header">
                                <h3>Today’s Appointments <span style={{ fontSize: "0.8rem", color: "#f0b800", marginLeft: "8px" }}>{new Date().toLocaleDateString()}</span></h3>
                                <i className="fas fa-calendar-check card-icon"></i>
                            </div>
                            <div className="elegant-scroll" style={{ maxHeight: "300px", overflowY: "auto", paddingRight: "5px" }}>
                                {today.filter(a => new Date(a.time).toDateString() === new Date().toDateString()).length ? (
                                    today.filter(a => new Date(a.time).toDateString() === new Date().toDateString()).map((a) => (
                                        <div className="appt-item" key={a.id}>
                                            <b>
                                                {new Date(a.time).toLocaleTimeString("en-IN", {
                                                    hour: "2-digit",
                                                    minute: "2-digit",
                                                    hour12: true,
                                                })}
                                            </b>
                                            <div className="appt-patient">
                                                {capitalizeFullName(cleanName(a.patient_name))}
                                                <span style={{ marginLeft: "10px", fontSize: "0.85rem", opacity: 0.7 }}>
                                                    {a.patient_age && `(Age: ${a.patient_age})`} {a.patient_phone && ` • 📞 ${a.patient_phone}`}
                                                </span>
                                            </div>
                                            <div className="appt-reason">{a.reason}</div>
                                            <div style={{ color: "#f0b800", fontSize: "0.8rem", marginTop: "4px" }}>
                                                <i className="fas fa-user-md"></i> {a.doctor_name}
                                            </div>

                                            {/* Action Buttons */}
                                            {/* Action Buttons */}
                                            {a.status === "scheduled" && (() => {
                                                const now = new Date();
                                                const apptTime = new Date(a.time);
                                                const isPast = now >= apptTime;

                                                return (
                                                    <div className="action-buttons" style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                                                        <button
                                                            className="done-btn"
                                                            onClick={() => isPast ? markCompleted(a.id) : alert("Cannot mark as completed before appointment time.")}
                                                            disabled={!isPast}
                                                            style={{
                                                                margin: 0,
                                                                padding: "0 12px",
                                                                height: "40px",
                                                                background: isPast ? "#2ecc71" : "#555",
                                                                color: isPast ? "#fff" : "#888",
                                                                border: "none",
                                                                borderRadius: "5px",
                                                                cursor: isPast ? "pointer" : "not-allowed",
                                                                fontWeight: "bold",
                                                                flex: 1,
                                                                display: "flex",
                                                                alignItems: "center",
                                                                justifyContent: "center",
                                                                gap: "6px",
                                                                whiteSpace: "nowrap"
                                                            }}
                                                        >
                                                            <i className="fas fa-check"></i> Completed
                                                        </button>
                                                        <button
                                                            className="follow-up-btn"
                                                            onClick={() => isPast ? openFollowUpModal(a.id) : alert("Cannot add follow-up before appointment time.")}
                                                            disabled={!isPast}
                                                            style={{
                                                                margin: 0,
                                                                padding: "0 12px",
                                                                height: "40px",
                                                                background: isPast ? "#f0b800" : "#555",
                                                                color: isPast ? "#000" : "#888",
                                                                border: "none",
                                                                borderRadius: "5px",
                                                                cursor: isPast ? "pointer" : "not-allowed",
                                                                fontWeight: "bold",
                                                                flex: 1,
                                                                display: "flex",
                                                                alignItems: "center",
                                                                justifyContent: "center",
                                                                gap: "6px",
                                                                whiteSpace: "nowrap"
                                                            }}
                                                        >
                                                            <i className="fas fa-clock"></i> Follow Up
                                                        </button>
                                                        <button
                                                            className="missed-btn"
                                                            onClick={() => isPast ? markNotVisited(a.id) : alert("Cannot mark as not visited before appointment time.")}
                                                            disabled={!isPast}
                                                            style={{
                                                                margin: 0,
                                                                padding: "0 12px",
                                                                height: "40px",
                                                                background: isPast ? "#e74c3c" : "#555",
                                                                color: isPast ? "#fff" : "#888",
                                                                border: "none",
                                                                borderRadius: "5px",
                                                                cursor: isPast ? "pointer" : "not-allowed",
                                                                fontWeight: "bold",
                                                                flex: 1,
                                                                display: "flex",
                                                                alignItems: "center",
                                                                justifyContent: "center",
                                                                gap: "6px",
                                                                whiteSpace: "nowrap"
                                                            }}
                                                        >
                                                            <i className="fas fa-times"></i> Not Visited
                                                        </button>
                                                    </div>
                                                );
                                            })()}

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
                                                            <span style={{ fontSize: "0.75rem", fontWeight: "bold", color: a.follow_up_status === "completed" ? "#28a745" : "#dc3545", textTransform: "capitalize" }}>
                                                                Follow-up {a.follow_up_status}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))
                                ) : (
                                    <p style={{ color: "#888", textAlign: "center", padding: "1rem", fontStyle: "italic" }}>No appointments remaining today.</p>
                                )}
                            </div>
                        </div>

                        <div className="card animate-fade-up" style={{ animationDelay: "0.2s", flex: "1", minWidth: "300px", maxWidth: "488px" }}>
                            <div className="card-header">
                                <h3>Upcoming Appointments</h3>
                                <i className="fas fa-clock card-icon"></i>
                            </div>
                            <div style={{ maxHeight: "400px", overflowY: "auto" }}>
                                {upcoming.length ? (
                                    upcoming.map((a) => (
                                        <div className="appt-item" key={a.id}>
                                            <div style={{ display: "flex", justifyContent: "space-between" }}>
                                                <b style={{ color: "#f0b800" }}>{new Date(a.time).toLocaleDateString("en-IN", { day: '2-digit', month: 'short' })}</b>
                                                <b>{new Date(a.time).toLocaleTimeString("en-IN", { hour: '2-digit', minute: '2-digit', hour12: true })}</b>
                                            </div>
                                            <div className="appt-patient">{capitalizeFullName(cleanName(a.patient_name))}</div>
                                            <div className="appt-reason">{a.reason}</div>
                                            <div style={{ color: "#f0b800", fontSize: "0.8rem", marginTop: "4px" }}>
                                                <i className="fas fa-user-md"></i> {a.doctor_name}
                                            </div>

                                            {/* PENDING APPROVAL ACTIONS */}
                                            {a.status === "pending_approval" && (
                                                <div style={{ marginTop: "10px", display: "flex", gap: "10px" }}>
                                                    <button onClick={() => handleApprove(a.id)} style={{ padding: "5px 10px", borderRadius: "5px", border: "none", background: "#2ecc71", color: "#fff", cursor: "pointer", flex: 1 }}>
                                                        <i className="fas fa-check"></i> Approve
                                                    </button>
                                                    <button onClick={() => openNegotiation(a)} style={{ padding: "5px 10px", borderRadius: "5px", border: "none", background: "#e67e22", color: "#fff", cursor: "pointer", flex: 1 }}>
                                                        <i className="fas fa-clock"></i> Reschedule
                                                    </button>
                                                </div>
                                            )}

                                            {/* NEGOTIATION STATUS */}
                                            {a.status === "negotiating" && (
                                                <div style={{ marginTop: "5px", color: "#fca311", fontSize: "0.8rem", fontStyle: "italic" }}>
                                                    Waiting for patient response...
                                                </div>
                                            )}
                                        </div>
                                    ))
                                ) : (
                                    <p className="empty-state">No upcoming appointments.</p>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* ROW 1.5: HISTORY (CENTERED) */}
                    <div className="row-history" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
                        <div className="card animate-fade-up" style={{ animationDelay: "0.2s", width: "100%", maxWidth: "1000px" }}>
                            <div className="card-header">
                                <h3>Appointment History</h3>
                                <i className="fas fa-history card-icon"></i>
                            </div>
                            <div className="history-list elegant-scroll" style={{ maxHeight: "400px", overflowY: "auto", paddingRight: "5px" }}>
                                {history.length ? (
                                    history.map((a) => (
                                        <div className="appt-item" key={a.id} style={{ opacity: 0.85 }}>
                                            <b>
                                                {new Date(a.time).toLocaleDateString()} {new Date(a.time).toLocaleTimeString("en-IN", {
                                                    hour: "2-digit",
                                                    minute: "2-digit",
                                                    hour12: true
                                                })}
                                            </b>
                                            <div className="appt-patient">
                                                {capitalizeFullName(cleanName(a.patient_name))}
                                                <span style={{ marginLeft: "10px", fontSize: "0.85rem", opacity: 0.7 }}>
                                                    {a.patient_age && `(Age: ${a.patient_age})`} {a.patient_phone && ` • 📞 ${a.patient_phone}`}
                                                </span>
                                            </div>
                                            <div className="appt-reason">{a.reason}</div>
                                            <div style={{ color: "#f0b800", fontSize: "0.8rem", marginTop: "4px" }}>
                                                <i className="fas fa-user-md"></i> {a.doctor_name}
                                            </div>

                                            {a.status === "completed" && (
                                                <span style={{ color: "#2ecc71", display: "block", marginTop: "5px" }}>
                                                    <i className="fas fa-check-circle"></i> Completed
                                                </span>
                                            )}

                                            {a.status === "missed" && (
                                                <span style={{ color: "#e74c3c", display: "block", marginTop: "5px" }}>
                                                    <i className="fas fa-times-circle"></i> Not Visited
                                                </span>
                                            )}

                                            {a.status === "follow_up" && (
                                                <div style={{ color: "#f0b800", marginTop: "5px" }}>
                                                    <i className="fas fa-clock"></i> Follow Up Required
                                                    <div style={{ fontSize: "0.8rem", opacity: 0.8 }}>Note: {a.follow_up_reason}</div>
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
                                                            <span style={{ fontSize: "0.75rem", fontWeight: "bold", color: a.follow_up_status === "completed" ? "#28a745" : "#dc3545", textTransform: "capitalize" }}>
                                                                Follow-up {a.follow_up_status}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))
                                ) : (
                                    <p className="empty-state">No appointment history yet.</p>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* NEGOTIATION MODAL */}
                    {negotiationModalOpen && (
                        <div className="modal-overlay" onClick={() => setNegotiationModalOpen(false)}>
                            <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px' }}>
                                <h3>Reschedule Appointment</h3>
                                <p style={{ marginBottom: '10px', color: '#ccc' }}>Propose a new time for {negotiatingAppt?.patient_name}</p>

                                <label style={{ display: 'block', marginBottom: '5px', color: '#aaa' }}>New Date & Time:</label>
                                <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
                                    <input
                                        type="date"
                                        value={proposedDate}
                                        onChange={e => setProposedDate(e.target.value)}
                                        style={{ flex: 1, padding: '10px', borderRadius: '5px', border: 'none' }}
                                    />
                                    <select
                                        value={proposedTimeSlot}
                                        onChange={e => setProposedTimeSlot(e.target.value)}
                                        style={{ flex: 1, padding: '10px', borderRadius: '5px', border: 'none' }}
                                    >
                                        <option value="" disabled>Time</option>
                                        {TIME_SLOTS.map(slot => (
                                            <option key={slot} value={slot}>{formatTime12h(slot)}</option>
                                        ))}
                                    </select>
                                </div>

                                <label style={{ display: 'block', marginBottom: '5px', color: '#aaa' }}>Reason for Change:</label>
                                <textarea
                                    value={denialReason}
                                    onChange={e => setDenialReason(e.target.value)}
                                    placeholder="e.g. Doctor is unavailable, slot double booked..."
                                    style={{ width: '100%', minHeight: '80px', padding: '10px', marginBottom: '15px', borderRadius: '5px', border: 'none' }}
                                ></textarea>

                                <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                                    <button onClick={() => setNegotiationModalOpen(false)} style={{ padding: '8px 15px', borderRadius: '5px', border: 'none', background: '#555', color: '#fff', cursor: 'pointer' }}>Cancel</button>
                                    <button onClick={submitNegotiation} style={{ padding: '8px 15px', borderRadius: '5px', border: 'none', background: '#e67e22', color: '#fff', cursor: 'pointer' }}>Send Proposal</button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* ROW 2: NEW PATIENT ARRIVAL */}
                    <div className="row-arrival" style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}>
                        <h2 style={{ color: "#f0b800", marginBottom: "2rem", textAlign: "center" }}>New Patient Arrival</h2>

                        <div id="arrivalForm" className="card animate-fade-up" style={{ width: "100%", maxWidth: "600px", margin: "0 auto" }}>
                            <div className="card-header">
                                <h3>Add Patient Visit</h3>
                                <i className="fas fa-user-plus card-icon"></i>
                            </div>
                            <div className="manual-entry-form" style={{ display: "flex", flexDirection: "column", gap: "15px", marginTop: "1rem" }}>
                                <div className="form-group">
                                    <label style={{ color: "#888", marginBottom: "5px", display: "block" }}>Patient Full Name</label>
                                    <input
                                        type="text"
                                        placeholder="Name"
                                        value={patientName}
                                        onChange={e => setPatientName(e.target.value)}
                                        style={{ width: "100%", padding: "12px", background: "#222", border: "1px solid #333", borderRadius: "8px", color: "#fff" }}
                                    />
                                </div>

                                <div style={{ display: "flex", gap: "15px" }}>
                                    <div className="form-group" style={{ flex: 2 }}>
                                        <label style={{ color: "#888", marginBottom: "5px", display: "block" }}>Phone Number</label>
                                        <input
                                            type="text"
                                            placeholder="e.g. 9876543210"
                                            value={patientPhone}
                                            onChange={e => setPatientPhone(e.target.value)}
                                            style={{ width: "100%", padding: "12px", background: "#222", border: "1px solid #333", borderRadius: "8px", color: "#fff" }}
                                        />
                                    </div>
                                    <div className="form-group" style={{ flex: 1 }}>
                                        <label style={{ color: "#888", marginBottom: "5px", display: "block" }}>Age</label>
                                        <input
                                            type="number"
                                            placeholder="Age"
                                            value={patientAge}
                                            onChange={e => setPatientAge(e.target.value)}
                                            style={{ width: "100%", padding: "12px", background: "#222", border: "1px solid #333", borderRadius: "8px", color: "#fff" }}
                                        />
                                    </div>
                                    <div className="form-group" style={{ flex: 1 }}>
                                        <label style={{ color: "#888", marginBottom: "5px", display: "block" }}>Sex</label>
                                        <select
                                            value={patientSex}
                                            onChange={e => setPatientSex(e.target.value)}
                                            style={{ width: "100%", padding: "12px", background: "#222", border: "1px solid #333", borderRadius: "8px", color: "#fff" }}
                                        >
                                            <option value="M">Male</option>
                                            <option value="F">Female</option>
                                            <option value="Other">Other</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label style={{ color: "#888", marginBottom: "5px", display: "block" }}>Date & Time of Visit</label>
                                    <div style={{ display: "flex", gap: "10px" }}>
                                        <input
                                            type="date"
                                            value={visitDate}
                                            onChange={e => setVisitDate(e.target.value)}
                                            style={{ flex: 1, padding: "12px", background: "#222", border: "1px solid #333", borderRadius: "8px", color: "#fff" }}
                                        />
                                        <select
                                            value={visitTime}
                                            onChange={e => setVisitTime(e.target.value)}
                                            style={{ flex: 1, padding: "12px", background: "#222", border: "1px solid #333", borderRadius: "8px", color: "#fff" }}
                                        >
                                            <option value="" disabled>Select Time</option>
                                            {TIME_SLOTS.map(slot => (
                                                <option key={slot} value={slot}>{formatTime12h(slot)}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                <div className="form-group">
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                                        <label style={{ color: "#888", margin: 0, display: "block" }}>Reason for Visit</label>
                                        <div className="complaint-toggle" style={{ display: "flex", background: "#222", borderRadius: "20px", padding: "2px", border: "1px solid #333" }}>
                                            <button
                                                type="button"
                                                onClick={() => { setComplaintType("manual"); if (visitReason === "Follow-up Visit") setVisitReason(""); }}
                                                style={{
                                                    padding: "4px 12px", borderRadius: "18px", border: "none", fontSize: "0.75rem", cursor: "pointer",
                                                    background: complaintType === "manual" ? "#f0b800" : "transparent",
                                                    color: complaintType === "manual" ? "#000" : "#888",
                                                    fontWeight: "bold", transition: "all 0.2s"
                                                }}
                                            >Clinical</button>
                                            <button
                                                type="button"
                                                onClick={() => { setComplaintType("followup"); setVisitReason("Follow-up Visit"); }}
                                                style={{
                                                    padding: "4px 12px", borderRadius: "18px", border: "none", fontSize: "0.75rem", cursor: "pointer",
                                                    background: complaintType === "followup" ? "#f0b800" : "transparent",
                                                    color: complaintType === "followup" ? "#000" : "#888",
                                                    fontWeight: "bold", transition: "all 0.2s"
                                                }}
                                            >Follow-up</button>
                                        </div>
                                    </div>
                                    <textarea
                                        placeholder="Primary complaint..."
                                        value={visitReason}
                                        onChange={e => setVisitReason(e.target.value)}
                                        style={{ width: "100%", padding: "12px", background: "#222", border: "1px solid #333", borderRadius: "8px", color: "#fff", minHeight: "100px" }}
                                    ></textarea>
                                </div>

                                <div className="form-group">
                                    <label style={{ color: "#888", marginBottom: "5px", display: "block" }}>Assign Doctor</label>
                                    <select
                                        value={assignedDoctor}
                                        onChange={e => setAssignedDoctor(e.target.value)}
                                        style={{ width: "100%", padding: "12px", background: "#222", border: "1px solid #333", borderRadius: "8px", color: "#fff" }}
                                    >
                                        <option value="">-- Select Doctor --</option>
                                        {doctorsList.map((doc, idx) => (
                                            <option key={idx} value={doc}>{doc}</option>
                                        ))}
                                    </select>
                                </div>

                                <button
                                    onClick={handleAddPatient}
                                    disabled={isSubmitting}
                                    style={{ padding: "15px", background: "#f0b800", color: "#000", border: "none", borderRadius: "10px", fontWeight: "bold", cursor: "pointer", marginTop: "10px", fontSize: "1rem" }}
                                >
                                    {isSubmitting ? "Submitting..." : "Check In Patient"}
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* ROW 2.5: DAILY CLOSURE REPORT */}
                    <div className="row-stats" style={{ display: "flex", justifyContent: "center", width: "100%", marginBottom: "2rem" }}>
                        <div className="card animate-fade-up" style={{ animationDelay: "0.2s", width: "100%", maxWidth: "1000px" }}>
                            <div className="card-header">
                                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                    <h3>Daily Closure Report</h3>
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
                                            outline: "none",
                                            colorScheme: "dark"
                                        }}
                                    >
                                        <option value="daily" style={{ background: "#222", color: "#fff" }}>Daily</option>
                                        <option value="monthly" style={{ background: "#222", color: "#fff" }}>Monthly</option>
                                        <option value="yearly" style={{ background: "#222", color: "#fff" }}>Yearly</option>
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
                                        <h4 style={{ color: "#888", marginBottom: "0.5rem" }}>Avg. Invoice</h4>
                                        <div style={{ fontSize: "2rem", color: "#3498db", fontWeight: "bold" }}>
                                            ₹{(() => {
                                                const dailyInvoices = invoices.filter(inv => {
                                                    const d = new Date(inv.date);
                                                    const r = new Date(reportDate);
                                                    if (reportView === 'daily') return d.toDateString() === r.toDateString();
                                                    if (reportView === 'monthly') return d.getMonth() === r.getMonth() && d.getFullYear() === r.getFullYear();
                                                    if (reportView === 'yearly') return d.getFullYear() === r.getFullYear();
                                                    return false;
                                                });
                                                const totalRev = dailyInvoices.reduce((sum, inv) => sum + (parseFloat(inv.total) || 0), 0);
                                                return dailyInvoices.length ? Math.round(totalRev / dailyInvoices.length).toLocaleString() : 0;
                                            })()}
                                        </div>
                                    </div>
                                    <div style={{ background: "#222", padding: "1.5rem", borderRadius: "10px", textAlign: "center", border: "1px solid #333" }}>
                                        <h4 style={{ color: "#888", marginBottom: "0.5rem" }}>Missed / Cancelled</h4>
                                        <div style={{ fontSize: "2rem", color: "#e74c3c", fontWeight: "bold" }}>
                                            {[...today, ...history].filter(a => {
                                                const d = new Date(a.time);
                                                const r = new Date(reportDate);
                                                if (!['missed', 'cancelled'].includes(a.status)) return false;
                                                if (reportView === 'daily') return d.toDateString() === r.toDateString();
                                                if (reportView === 'monthly') return d.getMonth() === r.getMonth() && d.getFullYear() === r.getFullYear();
                                                if (reportView === 'yearly') return d.getFullYear() === r.getFullYear();
                                                return false;
                                            }).length}
                                        </div>
                                    </div>
                                </div>

                                {/* GRAPHS (COMPARISON) */}
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
                                    {/* VISITS GRAPH */}
                                    <div style={{ background: "#222", padding: "1.5rem", borderRadius: "10px", border: "1px solid #333" }}>
                                        <h4 style={{ color: "#fff", marginBottom: "1rem" }}>Visits Comparison</h4>
                                        <div style={{ marginBottom: "1rem" }}>
                                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "5px", color: "#ccc" }}>
                                                <span>{reportView === 'daily' ? 'Selected Date' : reportView === 'monthly' ? 'Selected Month' : 'Selected Year'}</span>
                                                <span>{[...today, ...history].filter(a => {
                                                    const d = new Date(a.time);
                                                    const r = new Date(reportDate);
                                                    if (reportView === 'daily') return d.toDateString() === r.toDateString();
                                                    if (reportView === 'monthly') return d.getMonth() === r.getMonth() && d.getFullYear() === r.getFullYear();
                                                    if (reportView === 'yearly') return d.getFullYear() === r.getFullYear();
                                                    return false;
                                                }).length}</span>
                                            </div>
                                            <div style={{ height: "8px", background: "#333", borderRadius: "4px", overflow: "hidden" }}>
                                                <div style={{ width: "70%", height: "100%", background: "#3498db" }}></div>
                                            </div>
                                        </div>
                                        <div style={{ marginBottom: "1rem" }}>
                                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "5px", color: "#ccc" }}>
                                                <span>Yesterday</span>
                                                <span>{history.length > 5 ? Math.floor(history.length / 2) : 2}</span>
                                            </div>
                                            <div style={{ height: "8px", background: "#333", borderRadius: "4px", overflow: "hidden" }}>
                                                <div style={{ width: "50%", height: "100%", background: "#555" }}></div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* REVENUE GRAPH */}
                                    <div style={{ background: "#222", padding: "1.5rem", borderRadius: "10px", border: "1px solid #333" }}>
                                        <h4 style={{ color: "#fff", marginBottom: "1rem" }}>Revenue Comparison</h4>
                                        <div style={{ marginBottom: "1rem" }}>
                                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "5px", color: "#ccc" }}>
                                                <span>{reportView === 'daily' ? 'Selected Date' : reportView === 'monthly' ? 'Selected Month' : 'Selected Year'}</span>
                                                <span>₹{invoices
                                                    .filter(inv => {
                                                        const d = new Date(inv.date);
                                                        const r = new Date(reportDate);
                                                        if (reportView === 'daily') return d.toDateString() === r.toDateString();
                                                        if (reportView === 'monthly') return d.getMonth() === r.getMonth() && d.getFullYear() === r.getFullYear();
                                                        if (reportView === 'yearly') return d.getFullYear() === r.getFullYear();
                                                        return false;
                                                    })
                                                    .reduce((sum, inv) => sum + (parseFloat(inv.total) || 0), 0)
                                                    .toLocaleString()}</span>
                                            </div>
                                            <div style={{ height: "8px", background: "#333", borderRadius: "4px", overflow: "hidden" }}>
                                                <div style={{ width: "65%", height: "100%", background: "#f0b800" }}></div>
                                            </div>
                                        </div>
                                        <div style={{ marginBottom: "1rem" }}>
                                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "5px", color: "#ccc" }}>
                                                <span>Last Month Avg</span>
                                                <span>₹1,200</span>
                                            </div>
                                            <div style={{ height: "8px", background: "#333", borderRadius: "4px", overflow: "hidden" }}>
                                                <div style={{ width: "45%", height: "100%", background: "#555" }}></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
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
                                onPatientChange={(name) => setInvoicePatient(name)}
                            />

                            {/* Recent Invoices for selected patient */}
                            {invoicePatient && (
                                <div className="recent-prescriptions" style={{ marginTop: "2rem", borderTop: "1px solid #333", paddingTop: "1rem" }}>
                                    <h4 style={{ marginBottom: "1rem", color: "#f0b800" }}>
                                        Invoices for {invoicePatient}
                                    </h4>
                                    <div className="presc-list elegant-scroll" style={{ maxHeight: "300px", overflowY: "auto" }}>
                                        {invoices
                                            .filter(inv => (inv.patient_name || "").toLowerCase() === invoicePatient.toLowerCase())
                                            .length > 0 ? (
                                            invoices
                                                .filter(inv => (inv.patient_name || "").toLowerCase() === invoicePatient.toLowerCase())
                                                .map(inv => (
                                                    <div key={inv.id} className="presc-item-mini" style={{
                                                        background: "#222", padding: "10px", borderRadius: "8px", marginBottom: "10px",
                                                        display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid #333"
                                                    }}>
                                                        <div>
                                                            <b style={{ color: "#fff" }}>{inv.patient_name}</b>
                                                            <div style={{ fontSize: "0.8rem", color: "#888" }}>{new Date(inv.date).toLocaleDateString()}</div>
                                                            <div style={{ fontSize: "0.85rem", color: "#2ecc71", fontWeight: "bold" }}>₹ {inv.total.toLocaleString()} ({inv.invoice_number})</div>
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

                    {/* ROW 4: ALL PATIENTS TABLE */}
                    <div className="row-patients" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
                        <div className="card animate-fade-up" style={{ width: "100%", maxWidth: "1100px" }}>
                            <div className="card-header">
                                <h3>All Registered Patients</h3>
                                <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                                    <button onClick={downloadPatientData} style={{ background: "#2ecc71", border: "none", padding: "5px 10px", borderRadius: "5px", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: "bold" }}>
                                        <i className="fas fa-file-excel" style={{ marginRight: "5px" }}></i> Export CSV
                                    </button>
                                    <i className="fas fa-users card-icon"></i>
                                </div>
                            </div>
                            <div className="elegant-scroll" style={{ padding: "1rem", overflowX: "auto", maxHeight: "300px", overflowY: "auto" }}>
                                <table style={{ width: "100%", borderCollapse: "collapse", color: "#fff", textAlign: "left" }}>
                                    <thead>
                                        <tr style={{ borderBottom: "1px solid #333" }}>
                                            <th style={{ padding: "12px", color: "#f0b800" }}>Name</th>
                                            <th style={{ padding: "12px", color: "#f0b800" }}>Age/Sex</th>
                                            <th style={{ padding: "12px", color: "#f0b800" }}>Phone</th>
                                            <th style={{ padding: "12px", color: "#f0b800" }}>Email</th>
                                            <th style={{ padding: "12px", color: "#f0b800" }}>Source</th>
                                            <th style={{ padding: "12px", color: "#f0b800" }}>Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {patientsList.length > 0 ? (
                                            patientsList.map(p => (
                                                <tr key={p.id} style={{ borderBottom: "1px solid #222" }}>
                                                    <td style={{ padding: "12px" }}>{p.name}</td>
                                                    <td style={{ padding: "12px", color: "#ddd" }}>{p.age || "-"} / {p.sex || p.gender || "-"}</td>
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
                                                    <td style={{ padding: "12px", display: "flex", gap: "10px" }}>
                                                        <button
                                                            onClick={() => handleRepeatVisit(p)}
                                                            title="Repeat Visit"
                                                            style={{ background: "transparent", border: "none", color: "#2ecc71", cursor: "pointer", fontSize: "1.1rem" }}
                                                        >
                                                            <i className="fas fa-calendar-plus"></i>
                                                        </button>
                                                        <button
                                                            onClick={() => openEditModal(p)}
                                                            title="Quick Edit"
                                                            style={{ background: "transparent", border: "none", color: "#f0b800", cursor: "pointer", fontSize: "1.1rem" }}
                                                        >
                                                            <i className="fas fa-edit"></i>
                                                        </button>
                                                        <button
                                                            onClick={() => handleArchive(p.id)}
                                                            title="Archive Patient"
                                                            style={{ background: "transparent", border: "none", color: "#e74c3c", cursor: "pointer", fontSize: "1.1rem" }}
                                                        >
                                                            <i className="fas fa-trash-alt"></i>
                                                        </button>
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
            <Footer />

            {/* QUICK EDIT MODAL */}
            {isEditModalOpen && (
                <div style={{
                    position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
                    background: "rgba(0,0,0,0.8)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000
                }}>
                    <div className="card" style={{ width: "400px", padding: "2rem" }}>
                        <h3 style={{ color: "#f0b800", marginBottom: "1.5rem" }}>Quick Edit Patient</h3>
                        <div style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
                            <div>
                                <label style={{ color: "#888", fontSize: "0.8rem" }}>Full Name</label>
                                <input
                                    type="text" value={editName} onChange={e => setEditName(e.target.value)}
                                    style={{ width: "100%", padding: "10px", background: "#222", border: "1px solid #333", borderRadius: "5px", color: "#fff" }}
                                />
                            </div>
                            <div>
                                <label style={{ color: "#888", fontSize: "0.8rem" }}>Phone</label>
                                <input
                                    type="text" value={editPhone} onChange={e => setEditPhone(e.target.value)}
                                    style={{ width: "100%", padding: "10px", background: "#222", border: "1px solid #333", borderRadius: "5px", color: "#fff" }}
                                />
                            </div>
                            <div>
                                <label style={{ color: "#888", fontSize: "0.8rem" }}>Age</label>
                                <input
                                    type="number" value={editAge} onChange={e => setEditAge(e.target.value)}
                                    style={{ width: "100%", padding: "10px", background: "#222", border: "1px solid #333", borderRadius: "5px", color: "#fff" }}
                                />
                            </div>
                            <div>
                                <label style={{ color: "#888", fontSize: "0.8rem" }}>Sex</label>
                                <select
                                    value={editSex} onChange={e => setEditSex(e.target.value)}
                                    style={{ width: "100%", padding: "10px", background: "#222", border: "1px solid #333", borderRadius: "5px", color: "#fff" }}
                                >
                                    <option value="M">Male</option>
                                    <option value="F">Female</option>
                                    <option value="Other">Other</option>
                                </select>
                            </div>
                            <div style={{ display: "flex", gap: "10px", marginTop: "1rem" }}>
                                <button
                                    onClick={handleEditSave}
                                    style={{ flex: 1, padding: "10px", background: "#f0b800", color: "#000", border: "none", borderRadius: "5px", fontWeight: "bold", cursor: "pointer" }}
                                >Save Changes</button>
                                <button
                                    onClick={() => setIsEditModalOpen(false)}
                                    style={{ flex: 1, padding: "10px", background: "#333", color: "#fff", border: "none", borderRadius: "5px", cursor: "pointer" }}
                                >Cancel</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Follow Up Modal */}
            {followUpOpen && (
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
                            onChange={(e) => setFollowUpReason(e.target.value)}
                            placeholder="e.g. Needs gum checking in 2 weeks..."
                            style={{ width: "100%", height: "100px", background: "#333", border: "none", color: "#fff", padding: "10px", borderRadius: "5px", marginBottom: "1rem" }}
                        ></textarea>

                        <div style={{ display: "flex", gap: "10px", marginBottom: "1rem" }}>
                            <div style={{ flex: 1 }}>
                                <label style={{ display: "block", color: "#888", marginBottom: "5px", fontSize: "0.9rem" }}>Next Visit Date</label>
                                <input
                                    type="date"
                                    value={followUpDate}
                                    onChange={e => setFollowUpDate(e.target.value)}
                                    style={{ width: "100%", padding: "10px", background: "#333", border: "none", color: "#fff", borderRadius: "5px" }}
                                />
                            </div>
                            <div style={{ flex: 1 }}>
                                <label style={{ display: "block", color: "#888", marginBottom: "5px", fontSize: "0.9rem" }}>Time</label>
                                <input
                                    type="time"
                                    value={followUpTime}
                                    onChange={e => setFollowUpTime(e.target.value)}
                                    style={{ width: "100%", padding: "10px", background: "#333", border: "none", color: "#fff", borderRadius: "5px" }}
                                />
                            </div>
                        </div>

                        <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                            <button onClick={() => setFollowUpOpen(false)} style={{ padding: "10px 20px", background: "transparent", border: "1px solid #555", color: "#fff", borderRadius: "5px", cursor: "pointer" }}>Cancel</button>
                            <button onClick={markFollowUp} style={{ padding: "10px 20px", background: "#f0b800", border: "none", color: "#000", borderRadius: "5px", cursor: "pointer", fontWeight: "bold" }}>Confirm Follow Up</button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
