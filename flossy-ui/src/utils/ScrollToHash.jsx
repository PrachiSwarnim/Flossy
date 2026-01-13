import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export default function ScrollToHash() {
  const { hash } = useLocation();

  useEffect(() => {
    if (hash && !hash.includes("?") && !hash.includes("=")) {
      try {
        const el = document.querySelector(hash);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      } catch (e) {
        console.warn("Invalid hash selector:", hash);
      }
    }
  }, [hash]);

  return null;
}
