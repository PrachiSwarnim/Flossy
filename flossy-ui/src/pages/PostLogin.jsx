import { useEffect } from "react";
import { useUser, useSession } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";

export default function PostLogin() {
  const { user, isLoaded } = useUser();
  const { session } = useSession();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoaded) return;

    if (!user) {
      navigate("/login");
      return;
    }

    session.getToken().then((token) => {
      sessionStorage.setItem("flossy_token", token);
      sessionStorage.setItem("flossy_user", JSON.stringify(user));
      navigate("/role_selection");
    });
  }, [isLoaded, session, user, navigate]);

  return (
    <div style={{ padding: "5rem", textAlign: "center" }}>
      <h2>Setting up your account…</h2>
    </div>
  );
}
