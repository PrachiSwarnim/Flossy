import { useNavigate } from "react-router-dom";
import Header from "./dashboards/DashboardHeader";
import Footer from "../components/Footer";

export default function NotAuthorized() {
    const navigate = useNavigate();

    return (
        <div style={{ background: "var(--bg-dark)", minHeight: "100vh", color: "var(--text-light)" }}>
            <Header />
            <main style={{ padding: "4rem 2rem", textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                <i className="fas fa-lock" style={{ fontSize: "4rem", color: "#dc3545", marginBottom: "2rem" }}></i>
                <h1 style={{ fontSize: "2.5rem", marginBottom: "1rem", color: "#f0b800" }}>Access Denied</h1>
                <p style={{ fontSize: "1.2rem", color: "#888", maxWidth: "500px", marginBottom: "2.5rem" }}>
                    You don't have the required permissions to access this page.
                </p>
                <button
                    onClick={() => navigate("/")}
                    style={{
                        padding: "15px 40px",
                        background: "#f0b800",
                        color: "#000",
                        border: "none",
                        borderRadius: "50px",
                        fontWeight: "bold",
                        cursor: "pointer",
                        fontSize: "1.1rem",
                        boxShadow: "0 10px 20px rgba(0,0,0,0.3)"
                    }}
                >
                    Return Home
                </button>
            </main>
            <Footer />
        </div>
    );
}
