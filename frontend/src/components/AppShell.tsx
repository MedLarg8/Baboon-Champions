import { Crown, Home, Users } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

export function AppShell() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink className="brand" to="/" aria-label="ARAM Baboon Tracker home">
          <span className="brand-mark">
            <Crown size={21} aria-hidden="true" />
          </span>
          <span>
            <strong>ARAM Baboon Tracker</strong>
            <small>Mayhem friend group ledger</small>
          </span>
        </NavLink>

        <nav className="topnav" aria-label="Primary">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            <Home size={18} aria-hidden="true" />
            <span>Dashboard</span>
          </NavLink>
          <NavLink to="/friends" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            <Users size={18} aria-hidden="true" />
            <span>Friends</span>
          </NavLink>
        </nav>
      </header>

      <main className="content-shell">
        <Outlet />
      </main>
    </div>
  );
}
