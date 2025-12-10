import { SignedIn, UserButton, useClerk } from "@clerk/clerk-react";

export default function DashboardHeader() {
  const { signOut } = useClerk();

  return (
    <header className="dash-header">
      <h2>Welcome to Your Dashboard</h2>

      <SignedIn>
        <button
          className="logout-btn"
          onClick={() => signOut(() => (window.location.href = "/"))}
        >
          Logout
        </button>

        <UserButton afterSignOutUrl="/" />
      </SignedIn>
    </header>
  );
}
