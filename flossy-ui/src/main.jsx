import React from "react";
import ReactDOM from "react-dom/client";
import { ClerkProvider } from "@clerk/clerk-react";
import App from "./App.jsx";
import "./index.css";
import "./styles/global.css";

const PUBLISHABLE_KEY = "pk_live_Y2xlcmsuc21pbGVhcnRpc3RzZGVudGFsc3R1ZGlvLmNvbSQ";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ClerkProvider publishableKey={PUBLISHABLE_KEY}>
      <App />
    </ClerkProvider>
  </React.StrictMode>
);
