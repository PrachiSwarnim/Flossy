import { useState, useEffect } from "react";
import { useUser, useSession, useClerk } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import "../styles/appointment_form.css";
import { TIME_SLOTS, formatTime12h } from "../utils/timeSlots";
import { COUNTRY_CODES } from "../utils/countryCodes";

const getFlagEmoji = (isoCode) => {
    if (!isoCode) return "🌐";
    return isoCode
        .toUpperCase()
        .replace(/./g, (char) =>
            String.fromCodePoint(char.charCodeAt(0) + 127397)
        );
};

export default function AppointmentRequestForm({ className }) {
    const { isSignedIn, user } = useUser();
    const { session } = useSession(); // Get session for token
    const { openSignIn } = useClerk();
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        name: "",
        phone: "",
        reason: "",
        date: "",
        time: "",
        age: "",
        sex: "",
        countryCode: "+91"
    });
    const [showCountrySearch, setShowCountrySearch] = useState(false);
    const [countrySearch, setCountrySearch] = useState("");
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    useEffect(() => {
        if (isSignedIn && user) {
            const capitalizeFullName = (name) => {
                if (!name || typeof name !== 'string') return "";
                const localPart = name.split('@')[0];
                let parts = localPart.split(/[._-]/);
                const titles = ['mr', 'ms', 'mrs', 'dr', 'prof'];
                parts = parts.filter(part => !titles.includes(part.toLowerCase()));
                if (parts.length === 0) return "";
                // DO NOT REVERSE - keep names in order
                return parts.map(part => {
                    const cleanPart = part.replace(/\d+/g, "");
                    return cleanPart.charAt(0).toUpperCase() + cleanPart.slice(1).toLowerCase();
                }).filter(p => p.length > 0).join(' ');
            };

            const userEmail = user?.primaryEmailAddress?.emailAddress || "";
            // Prioritize fullName from Clerk
            const clerkName = user?.fullName || (user?.firstName ? `${user.firstName} ${user.lastName || ""}`.trim() : null);
            const fullName = clerkName || capitalizeFullName(userEmail);

            if (fullName) {
                setFormData(prev => ({ ...prev, name: fullName }));
            }
        }
    }, [isSignedIn, user]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        const API = import.meta.env.VITE_API_BASE_URL;

        if (isSignedIn && session) {
            try {
                const token = await session.getToken({ template: "default" });

                if (!formData.date || !formData.time) {
                    alert("Please select both date and time.");
                    setLoading(false);
                    return;
                }

                const isoDate = new Date(`${formData.date}T${formData.time}`).toISOString();

                const res = await fetch(`${API}/api/appointments/`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        datetime: isoDate,
                        reason: formData.reason,
                        phone: `${formData.countryCode}${formData.phone}`,
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

                        <div className="input-group" style={{ display: "flex", gap: "10px", position: "relative" }}>
                             <div style={{ width: "120px", position: "relative" }}>
                                <input
                                    type="text"
                                    placeholder="Code"
                                    value={showCountrySearch ? countrySearch : formData.countryCode}
                                    onChange={(e) => setCountrySearch(e.target.value)}
                                    onFocus={() => { setShowCountrySearch(true); setCountrySearch(""); }}
                                    style={{
                                        width: '100%',
                                        padding: '0.8rem',
                                        border: '1px solid rgba(255, 255, 255, 0.1)',
                                        background: 'rgba(255, 255, 255, 0.05)',
                                        borderRadius: '6px',
                                        color: '#f4f4f4'
                                    }}
                                />
                                {showCountrySearch && (
                                    <div className="elegant-scroll" style={{
                                        position: "absolute", bottom: "100%", left: 0,
                                        zIndex: 105, background: "#1a1a1a", border: "1px solid #444",
                                        borderRadius: "8px", marginBottom: "5px", maxHeight: "180px",
                                        overflowY: "auto", boxShadow: "0 -10px 25px rgba(0,0,0,0.5)", width: "220px"
                                    }}>
                                        {COUNTRY_CODES.filter(c =>
                                            c.name.toLowerCase().includes(countrySearch.toLowerCase()) ||
                                            c.code.includes(countrySearch) ||
                                            c.iso.toLowerCase().includes(countrySearch.toLowerCase())
                                        ).map(c => (
                                            <div key={c.iso} onClick={() => { setFormData(prev => ({...prev, countryCode: c.code})); setShowCountrySearch(false); }}
                                                style={{ padding: "10px", cursor: "pointer", borderBottom: "1px solid #333", color: "#fff", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "8px" }}>
                                                <span style={{ fontSize: "1.2rem" }}>{getFlagEmoji(c.iso)}</span>
                                                <span>{c.name} ({c.code})</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                             </div>
                            <input
                                type="tel"
                                name="phone"
                                placeholder="Phone Number"
                                required
                                value={formData.phone}
                                onChange={handleChange}
                                style={{ flex: 1 }}
                            />
                        </div>

                        <div style={{ display: "flex", gap: "15px", marginBottom: "1rem" }}>
                            <div className="input-group" style={{ flex: 1, position: "relative" }}>
                                <div className="input-icon-wrapper" style={{ height: "45px" }}>
                                    <i
                                        className="fas fa-calendar-alt"
                                        onClick={(e) => {
                                            const input = e.currentTarget.parentElement.querySelector('input');
                                            if (input) input.showPicker();
                                        }}
                                        style={{ cursor: 'pointer', pointerEvents: 'auto', left: '12px' }}
                                    ></i>
                                    <input
                                        type="date"
                                        name="date"
                                        required
                                        value={formData.date}
                                        onChange={handleChange}
                                        min={new Date().toISOString().split('T')[0]} // Prevents past dates
                                        style={{
                                            color: formData.date ? 'inherit' : '#999',
                                            padding: "0.8rem",
                                            paddingLeft: "42px",
                                            width: "100%",
                                            background: "rgba(255,255,255,0.05)",
                                            border: "1px solid rgba(255,255,255,0.1)",
                                            borderRadius: "6px",
                                            height: "100%"
                                        }}
                                        onClick={(e) => e.target.showPicker()}
                                    />
                                </div>
                            </div>
                            <div className="input-group" style={{ flex: 1 }}>
                                <select
                                    name="time"
                                    required
                                    value={formData.time}
                                    onChange={handleChange}
                                    style={{
                                        width: '100%',
                                        padding: '0.8rem',
                                        border: '1px solid rgba(255, 255, 255, 0.1)',
                                        background: 'rgba(255, 255, 255, 0.05)',
                                        borderRadius: '6px',
                                        fontSize: '0.95rem',
                                        color: formData.time ? '#f4f4f4' : '#888',
                                        height: '100%',
                                        appearance: 'none',
                                        cursor: 'pointer'
                                    }}
                                >
                                    <option value="" disabled>Select Time</option>
                                    {TIME_SLOTS.map(slot => (
                                        <option key={slot} value={slot}>{formatTime12h(slot)}</option>
                                    ))}
                                </select>
                            </div>
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
