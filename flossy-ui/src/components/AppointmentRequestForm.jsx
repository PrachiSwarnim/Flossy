import { useState } from "react";
import { useUser, useClerk } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import "../styles/appointment_form.css";

export default function AppointmentRequestForm() {
    const { isSignedIn, user } = useUser();
    const { openSignIn } = useClerk();
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        name: "",
        phone: "",
        reason: "",
    });
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        // If logged in, redirect to dashboard with pre-filled data (conceptually)
        // or just navigate them to dashboard to book.
        if (isSignedIn) {
            navigate("/patient");
            return;
        }

        // If guest, maybe we want to send this to backend?
        // For now, let's simulate sending a "Lead" or "Contact Request"
        // OR just prompt them to sign up to complete the booking.

        // Strategy: "To complete your booking, please sign in or create an account."
        // We can pass the state to the signup flow so it persists? 
        // For simplicity -> alert + redirect to signup.

        // BETTER UX: Send to backend as "Guest Inquiry" then prompt signup.
        try {
            const API = "http://localhost:8000";
            await fetch(`${API}/api/contact_request`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(formData)
            });

            alert("Thanks! We've received your request. Please sign in to finalize your appointment.");
            openSignIn({ afterSignInUrl: "/patient", afterSignUpUrl: "/patient" });

        } catch (err) {
            console.error("Error submitting form", err);
            // Fallback
            openSignIn();
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="appointment-section-wrapper">
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
                            <textarea
                                name="reason"
                                placeholder="Reason for Visit (e.g. Toothache, Checkup)"
                                rows="3"
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
