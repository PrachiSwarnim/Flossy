import { useEffect, useState } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import "../../styles/patient_dashboard.css";

export default function PatientDashboard() {
  const { user, isLoaded } = useUser();
  const { session } = useSession();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAppointments() {
      if (!session) return;

      try {
        const token = await session.getToken();

        const res = await fetch("/api/patient/appointments", {
          headers: { Authorization: `Bearer ${token}` },
        });

        const data = await res.json();
        setAppointments(data.appointments || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    loadAppointments();
  }, [session]);

  if (!isLoaded) return <div>Loading...</div>;

  return (
    <>
      <Header />
      <main className="patient-page">
        <section className="patient-hero">
          <h1>Welcome, {user.firstName}</h1>
          <p>Your upcoming appointments and activity overview</p>
        </section>

        <section className="patient-content">
          <div className="panel">
            <h2>Upcoming Appointments</h2>

            {loading ? (
              <p>Loading...</p>
            ) : appointments.length === 0 ? (
              <p>No upcoming appointments.</p>
            ) : (
              <ul className="appts">
                {appointments.map((a) => (
                  <li key={a.id}>
                    <strong>{a.date}</strong> — {a.service} with {a.provider_name}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="panel">
            <h2>Quick Actions</h2>
            <button>Book Appointment</button>
            <button>Contact Clinic</button>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
