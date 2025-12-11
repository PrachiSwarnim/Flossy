import { BrowserRouter, Routes, Route } from "react-router-dom";
import { SignedIn, SignedOut, RedirectToSignIn } from "@clerk/clerk-react";

import Home from "./pages/Home";
import Contact from "./pages/Contact";
import Services from "./pages/Services";
import Tourism from "./pages/DentalTourism";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import RoleSelection from "./pages/RoleSelection";
import PatientDashboard from "./pages/dashboards/PatientDashboard";
import DentistDashboard from "./pages/dashboards/DentistDashboard";
import PostLogin from "./pages/PostLogin";
import Team from "./components/Team";

import ScrollToHash from "./utils/ScrollToHash";

export default function App() {
  return (
    <BrowserRouter>
      <ScrollToHash />

      <Routes>
        {/* Public pages */}
        <Route path="/" element={<Home />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/services" element={<Services />} />
        <Route path="/tourism" element={<Tourism />} />
        <Route path="/team" element={<Team />} /> 

        {/* Auth pages */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/post_login" element={<PostLogin />} />

        {/* Protected routes */}
        <Route
          path="/role_selection"
          element={
            <SignedIn>
              <RoleSelection />
            </SignedIn>
          }
        />

        <Route
          path="/patient"
          element={
            <SignedIn>
              <PatientDashboard />
            </SignedIn>
          }
        />

        <Route
          path="/dentist"
          element={
            <SignedIn>
              <DentistDashboard />
            </SignedIn>
          }
        />

        {/* Redirect signed-out users */}
        <Route
          path="*"
          element={
            <SignedOut>
              <RedirectToSignIn />
            </SignedOut>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
