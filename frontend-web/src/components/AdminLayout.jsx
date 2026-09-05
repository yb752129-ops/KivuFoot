import { NavLink, Outlet, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function AdminLayout() {
  const nav = useNavigate();
  const { logout } = useAuth();

  async function out() {
    await logout();
    nav("/", { replace: true });
  }

  return (
    <div className="orga-app">
      <header className="orga-top">
        <div className="orga-top-inner">
          <Link to="/" className="wordmark-name">KivuFoot</Link>
          <p className="orga-comp">Administration</p>
          <button className="linkish" type="button" onClick={out}>
            Déconnexion
          </button>
        </div>
      </header>
      <nav className="orga-nav" aria-label="Administration">
        <NavLink to="/admin" end>Vue</NavLink>
        <NavLink to="/admin/audit">Audit</NavLink>
        <NavLink to="/admin/propositions">Propositions</NavLink>
      </nav>
      <div className="shell">
        <Outlet />
      </div>
    </div>
  );
}
