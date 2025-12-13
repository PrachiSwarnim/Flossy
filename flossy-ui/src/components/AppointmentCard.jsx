import React from "react";
import "../styles/dashboard_extras_patient.css";

export default function AppointmentCard({ appointment, onCancel }) {
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
                {appointment.status}
            </div>
        </div>
    );
}
