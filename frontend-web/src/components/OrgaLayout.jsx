import { NavLink, Outlet, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";

export default function OrgaLayout() {
  const nav = useNavigate();
  const { user, logout } = useAuth();
  const { competition } = useKivu();
  const role = user?.role;
  const bureau = role === "organisateur" || role === "admin";
  const nom = competition ? stripDemo(competition.nom) : "Aucune compétition";

  async function out() {
    await logout();
    nav("/", { replace: true });
  }

  return (
    <div className="orga-app">
      <header className="orga-top">
        <div className="orga-top-inner">
          <Link to="/" className="wordmark-name">KivuFoot</Link>
          <p className="orga-comp">{nom}</p>
          <button className="linkish" type="button" onClick={out}>
            Déconnexion
          </button>
        </div>
      </header>
      <nav className="orga-nav" aria-label="Organisation">
        {bureau && <NavLink to="/orga" end>Vue</NavLink>}
        {bureau && <NavLink to="/orga/equipes">Équipes</NavLink>}
        {bureau && <NavLink to="/orga/calendrier">Calendrier</NavLink>}
        <NavLink to="/orga/matchs">Matchs</NavLink>
      </nav>
      <div className="shell">
        <Outlet />
      </div>
    </div>
  );
}
