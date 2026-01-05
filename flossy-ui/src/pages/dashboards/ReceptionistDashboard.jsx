import { useEffect, useState } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { PropagateLoader } from "react-spinners";
import Header from "./DashboardHeader";
import Footer from "../../components/Footer";
import InvoiceForm from "../../components/InvoiceForm";
import "../../styles/dentist_dashboard.css";

const API = "http://localhost:8000";

export default function ReceptionistDashboard() {
    const { user, isLoaded } = useUser();
    const { session } = useSession();
    const navigate = useNavigate();

    const [pageLoading, setPageLoading] = useState(true);
    const [patientName, setPatientName] = useState("");
    const [patientPhone, setPatientPhone] = useState("");
    const [patientAge, setPatientAge] = useState("");
    const [visitDate, setVisitDate] = useState("");
    const [visitReason, setVisitReason] = useState("");
    const [assignedDoctor, setAssignedDoctor] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [patientsList, setPatientsList] = useState([]);
    const [invoices, setInvoices] = useState([]);
    const [today, setToday] = useState([]);
    const [upcoming, setUpcoming] = useState([]);
    const [doctorsList, setDoctorsList] = useState([]);

    // Edit Modal State
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editingPatient, setEditingPatient] = useState(null);
    const [editName, setEditName] = useState("");
    const [editPhone, setEditPhone] = useState("");
    const [editAge, setEditAge] = useState("");

    // Appointment Actions State
    const [followUpOpen, setFollowUpOpen] = useState(false);
    const [selectedApptId, setSelectedApptId] = useState(null);
    const [followUpReason, setFollowUpReason] = useState("");

    // === Full Name ===
    const fullName =
        `${user?.firstName || ""} ${user?.lastName || ""}`.trim() || "Receptionist";

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

    async function markFollowUp() {
        if (!followUpReason) return alert("Please enter a reason.");
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

    // 🔒 BLOCK ACCESS UNTIL LOADED
    useEffect(() => {
        if (!isLoaded) return;
        const role = user?.publicMetadata?.role;
        if (role !== "receptionist") {
            navigate("/not-authorized");
        }
        setPageLoading(false);
        fetchPatients();
        fetchInvoices();
        loadAppointments();
        fetchDoctors();
    }, [isLoaded, user, navigate]);


    async function fetchPatients() {
        const token = await session.getToken({ template: "default" });
        const res = await fetch(`${API}/api/patients`, {
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
        }
    }

    async function downloadInvoice(id, invNum) {
        const token = await session.getToken({ template: "default" });
        const res = await fetch(`${API}/api/invoices/${id}/pdf`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `invoice_${invNum}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        }
    }

    async function handleAddPatient() {
        if (!patientName || !patientPhone || !patientAge || !visitDate || !visitReason) {
            alert("Please fill in all details.");
            return;
        }

        setIsSubmitting(true);
        const token = await session.getToken({ template: "default" });

        try {
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
                    datetime: visitDate,
                    reason: visitReason,
                    doctor_name: assignedDoctor || null
                })
            });

            if (res.ok) {
                alert("Patient added successfully!");
                setPatientName("");
                setPatientPhone("");
                setPatientAge("");
                setVisitDate("");
                setVisitReason("");
                setAssignedDoctor("");
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
                    age: parseInt(editAge)
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

    return (
        <div className="receptionist-dashboard">
            <Header />
            <main className="dentist-main">
                <h2 id="Message">Welcome back, {fullName}!</h2>

                {/* QUICK GLANCE APPOINTMENTS */}
                <div className="grid" style={{ marginBottom: "3rem" }}>
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
                                            hour12: true,
                                        })}
                                    </b>
                                    <div style={{ color: "#fff", fontSize: "0.95rem", marginTop: "5px" }}>
                                        {a.patient_name} <span style={{ color: "#666", fontSize: "0.8rem" }}>
                                            ({a.patient_age || "N/A"}) {a.patient_phone && ` • 📞 ${a.patient_phone}`}
                                        </span>
                                    </div>
                                    <div style={{ color: "#888", fontSize: "0.85rem" }}>{a.reason}</div>
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
                            <p style={{ color: "#888", textAlign: "center", padding: "1rem" }}>No appointments for today.</p>
                        )}
                    </div>

                    <div className="card animate-fade-up" style={{ animationDelay: "0.2s" }}>
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
                                        <div style={{ color: "#fff", fontSize: "0.95rem", marginTop: "5px" }}>{a.patient_name}</div>
                                        <div style={{ color: "#888", fontSize: "0.85rem" }}>{a.reason}</div>
                                        <div style={{ color: "#f0b800", fontSize: "0.8rem", marginTop: "4px" }}>
                                            <i className="fas fa-user-md"></i> {a.doctor_name}
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <p style={{ color: "#888", textAlign: "center", padding: "1rem" }}>No upcoming appointments.</p>
                            )}
                        </div>
                    </div>
                </div>

                <h2 style={{ color: "#f0b800", marginBottom: "2rem" }}>Clinic Reception - New Patient Arrival</h2>

                <div id="arrivalForm" className="card animate-fade-up" style={{ maxWidth: "600px", margin: "0 auto" }}>
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
                        </div>

                        <div className="form-group">
                            <label style={{ color: "#888", marginBottom: "5px", display: "block" }}>Date & Time of Visit</label>
                            <input
                                type="datetime-local"
                                value={visitDate}
                                onChange={e => setVisitDate(e.target.value)}
                                style={{ width: "100%", padding: "12px", background: "#222", border: "1px solid #333", borderRadius: "8px", color: "#fff" }}
                            />
                        </div>

                        <div className="form-group">
                            <label style={{ color: "#888", marginBottom: "5px", display: "block" }}>Reason for Visit</label>
                            <textarea
                                placeholder="Primary complaint..."
                                value={visitReason}
                                onChange={e => setVisitReason(e.target.value)}
                                style={{ width: "100%", padding: "12px", background: "#222", border: "1px solid #333", borderRadius: "8px", color: "#fff", minHeight: "100px" }}
                            ></textarea>
                        </div>

                        <div className="form-group">
                            <label style={{ color: "#888", marginBottom: "5px", display: "block" }}>Assign Doctor (Optional)</label>
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

                {/* INVOICE SECTION */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem", marginTop: "3rem" }}>
                    <div className="card animate-fade-up">
                        <div className="card-header">
                            <h3>Generate New Invoice</h3>
                            <i className="fas fa-file-invoice-dollar card-icon"></i>
                        </div>
                        <InvoiceForm patientsList={patientsList} onInvoiceCreated={fetchInvoices} />
                    </div>

                    <div className="card animate-fade-up">
                        <div className="card-header">
                            <h3>Invoice History</h3>
                            <i className="fas fa-history card-icon"></i>
                        </div>
                        <div className="presc-list elegant-scroll" style={{ maxHeight: "600px", overflowY: "auto", marginTop: "1rem" }}>
                            {invoices.length > 0 ? (
                                invoices.map(inv => (
                                    <div key={inv.id} className="presc-item-mini" style={{
                                        background: "#222", padding: "12px", borderRadius: "8px", marginBottom: "12px",
                                        display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid #333"
                                    }}>
                                        <div>
                                            <b style={{ color: "#fff", display: "block" }}>{inv.patient_name}</b>
                                            <span style={{ fontSize: "0.8rem", color: "#f0b800" }}>{inv.invoice_number}</span>
                                            <div style={{ fontSize: "0.8rem", color: "#888" }}>{new Date(inv.date).toLocaleDateString()}</div>
                                            <div style={{ fontSize: "0.9rem", color: "#2ecc71", fontWeight: "bold" }}>{inv.currency} {inv.total.toLocaleString()}</div>
                                        </div>
                                        <button
                                            onClick={() => downloadInvoice(inv.id, inv.invoice_number)}
                                            style={{ background: "transparent", border: "1px solid #f0b800", color: "#f0b800", padding: "6px 12px", borderRadius: "4px", fontSize: "0.8rem", cursor: "pointer" }}
                                        >
                                            <i className="fas fa-download"></i> PDF
                                        </button>
                                    </div>
                                ))
                            ) : (
                                <p style={{ color: "#888", textAlign: "center" }}>No invoices generated yet.</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* ALL PATIENTS TABLE */}
                <div className="card animate-fade-up" style={{ marginTop: "3rem" }}>
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
                                    <th style={{ padding: "12px", color: "#f0b800" }}>Source</th>
                                    <th style={{ padding: "12px", color: "#f0b800" }}>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {patientsList.length > 0 ? (
                                    patientsList.map(p => (
                                        <tr key={p.id} style={{ borderBottom: "1px solid #222" }}>
                                            <td style={{ padding: "12px" }}>{p.name}</td>
                                            <td style={{ padding: "12px", color: "#888" }}>{p.phone}</td>
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
                <div className="modal-overlay">
                    <div className="modal-content" style={{ width: "400px" }}>
                        <h3>Mark for Follow Up</h3>
                        <p style={{ marginBottom: "1rem", color: "#ccc" }}>Enter reason for follow up:</p>
                        <textarea
                            value={followUpReason}
                            onChange={(e) => setFollowUpReason(e.target.value)}
                            rows="3"
                            style={{ width: "100%", padding: "10px", background: "#222", border: "1px solid #333", color: "#fff", marginBottom: "1rem" }}
                            placeholder="e.g. Check healing status..."
                        ></textarea>
                        <div style={{ display: "flex", gap: "10px" }}>
                            <button onClick={markFollowUp} style={{ flex: 1, padding: "10px", background: "#f0b800", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold" }}>Save</button>
                            <button onClick={() => setFollowUpOpen(false)} style={{ flex: 1, padding: "10px", background: "#333", border: "none", borderRadius: "5px", cursor: "pointer", color: "#fff" }}>Cancel</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
