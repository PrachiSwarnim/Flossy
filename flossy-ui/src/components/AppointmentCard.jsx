import React from "react";
import "../styles/dashboard_extras_patient.css";

export default function AppointmentCard({ appointment, onCancel, onAccept, onReschedule }) {
    if (!appointment) return null;

    const dateObj = new Date(appointment.time);
    const dateStr = dateObj.toLocaleDateString("en-IN", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
    });
    const timeStr = dateObj.toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
    });

    return (
        <div className="appt-card-item">
            <div className="ac-left">
                <div className="ac-date">
                    <span className="day">{dateObj.getDate()}</span>
                    <span className="month">{dateObj.toLocaleString("default", { month: "short" })}</span>
                </div>
                <div className="ac-details">
                    <h4>{appointment.reason || "General Checkup"}</h4>
                    <p>
                        <i className="fas fa-user-md"></i> {appointment.doctor_name || "Dr. Flossy Team"}
                    </p>
                    <p className="ac-time">
                        <i className="far fa-clock"></i> {dateStr} at {timeStr}
                    </p>
                </div>
            </div>

            {onCancel && (
                <button className="cancel-btn" onClick={() => onCancel(appointment.id)}>
                    Cancel
                </button>
            )}

            <div className={`status-badge ${appointment.status}`}>
                {appointment.status === "pending_approval" ? "Waiting for Approval" :
                    appointment.status === "negotiating" ? "Action Required" :
                        appointment.status}
            </div>

            {/* Negotiation Interface */}
            {appointment.status === "negotiating" && (
                <div className="negotiation-box" style={{ marginTop: '1rem', background: '#333', padding: '10px', borderRadius: '5px' }}>
                    <p style={{ color: '#fca311', fontSize: '0.9rem', marginBottom: '5px' }}>
                        <i className="fas fa-exclamation-circle"></i> Receptionist proposed a new time.
                    </p>
                    {appointment.denial_reason && (
                        <p style={{ fontSize: '0.85rem', color: '#ccc', marginBottom: '10px' }}>
                            "{appointment.denial_reason}"
                        </p>
                    )}
                    <div className="negotiation-actions" style={{ display: 'flex', gap: '10px' }}>
                        <button
                            onClick={() => onAccept && onAccept(appointment)}
                            style={{ background: '#4CAF50', color: 'white', border: 'none', padding: '5px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}
                        >
                            Accept
                        </button>
                        <button
                            onClick={() => onReschedule && onReschedule(appointment)}
                            style={{ background: '#fca311', color: 'black', border: 'none', padding: '5px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}
                        >
                            Propose New Time
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
