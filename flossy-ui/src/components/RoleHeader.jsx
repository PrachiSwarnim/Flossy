import { Link } from "react-router-dom";
import "../styles/role_header.css";

export default function RoleHeader() {
  return (
    <header className="role-header">
      <div className="role-header-logo">
        <img src="/static/assets/logo.png" alt="Smile Artists" />
        <span>Smile Artists</span>
      </div>

      <Link to="/" className="role-header-home">
        Home
      </Link>
    </header>
  );
}
