import { useState } from "react";
import { useUser, useSession, useClerk } from "@clerk/clerk-react"; // Added useSession
import { useNavigate } from "react-router-dom";
import "../styles/appointment_form.css";

export default function AppointmentRequestForm({ className }) {
    const { isSignedIn, user } = useUser();
    const { session } = useSession(); // Get session for token
    const { openSignIn } = useClerk();
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        name: "",
        phone: "",
        reason: "",
        datetime: "",
        age: "",
        sex: "",
    });
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        const API = import.meta.env.VITE_API_BASE_URL?.replace("http://", "https://");

        if (isSignedIn && session) {
            try {
                const token = await session.getToken({ template: "default" });
                const dt = new Date(formData.datetime);
                const isoDate = dt.toISOString();

                const res = await fetch(`${API}/api/appointments/`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        datetime: isoDate,
                        reason: formData.reason,
                        phone: formData.phone,
                        age: formData.age ? parseInt(formData.age) : null,
                        sex: formData.sex
                    })
                });

                if (res.ok) {
                    alert("Appointment Requested! Waiting for approval.");
                    if (window.location.pathname.includes("/patient")) {
                        window.location.reload();
                    } else {
                        navigate("/patient");
                    }
                } else {
                    const err = await res.json();
                    alert("Booking failed: " + (err.detail || "Unknown error"));
                }
            } catch (err) {
                console.error("Booking Error", err);
                alert("Something went wrong.");
            } finally {
                setLoading(false);
            }
            return;
        }

        navigate("/sign-in");
        setLoading(false);
    };

    return (
        <div className={`appointment-section-wrapper ${className || ""}`}>
            <div className="appointment-card">
                <div className="appointment-image">
                    <img src="/static/assets/Hollywood Smile Makeover.avif" alt="Smile Makeover" />
                    <div className="image-overlay">
                        <h4>Your New Smile Awaits</h4>
                    </div>
                </div>

                <div className="appointment-form-content">
                    <h3>Begin Your Smile Journey</h3>
                    <p>Ready for a transformation?</p>
                    <p className="subtitle-gap">Schedule your visit today.</p>

                    <form onSubmit={handleSubmit} className="appt-request-form">
                        <div className="input-group">
                            <input
                                type="text"
                                name="name"
                                placeholder="Patient Name"
                                required
                                value={formData.name}
                                onChange={handleChange}
                            />
                        </div>

                        <div style={{ display: "flex", gap: "15px", marginBottom: "0.5rem" }}>
                            <div className="input-group" style={{ flex: 1 }}>
                                <input
                                    type="number"
                                    name="age"
                                    placeholder="Age"
                                    value={formData.age}
                                    onChange={handleChange}
                                    style={{ padding: "0.8rem" }}
                                />
                            </div>
                            <div className="input-group" style={{ flex: 1.5 }}>
                                <select
                                    name="sex"
                                    value={formData.sex}
                                    onChange={handleChange}
                                    style={{
                                        width: '100%',
                                        padding: '0.8rem',
                                        border: '1px solid rgba(255, 255, 255, 0.1)',
                                        background: 'rgba(255, 255, 255, 0.05)',
                                        borderRadius: '6px',
                                        fontSize: '0.95rem',
                                        color: formData.sex ? '#f4f4f4' : '#888',
                                        height: '100%',
                                        appearance: 'none',
                                        cursor: 'pointer'
                                    }}
                                >
                                    <option value="" disabled>Sex</option>
                                    <option value="Male">Male</option>
                                    <option value="Female">Female</option>
                                    <option value="Other">Other</option>
                                </select>
                            </div>
                        </div>

                        <div className="input-group">
                            <input
                                type="tel"
                                name="phone"
                                placeholder="Phone Number"
                                required
                                value={formData.phone}
                                onChange={handleChange}
                            />
                        </div>

                        <div className="input-group">
                            <input
                                type="datetime-local"
                                name="datetime"
                                required
                                value={formData.datetime}
                                onChange={handleChange}
                                style={{ color: formData.datetime ? 'inherit' : '#999' }}
                            />
                        </div>

                        <div className="input-group">
                            <textarea
                                name="reason"
                                placeholder="Reason for Visit (e.g. Toothache, Checkup)"
                                rows="2"
                                value={formData.reason}
                                onChange={handleChange}
                            ></textarea>
                        </div>

                        <button type="submit" disabled={loading} className="submit-btn">
                            {loading ? "Processing..." : (isSignedIn ? "Book via Dashboard" : "Schedule Consultation")}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
