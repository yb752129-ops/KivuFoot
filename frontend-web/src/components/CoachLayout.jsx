import { NavLink, Outlet, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { clubName, useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";

export default function CoachLayout() {
  const nav = useNavigate();
  const { user, logout } = useAuth();
  const { clubsById } = useKivu();
  const nom = user?.club_id
    ? stripDemo(clubName(clubsById, user.club_id))
    : "Aucun club rattaché";

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
      <nav className="orga-nav" aria-label="Coach">
        <NavLink to="/coach" end>Club</NavLink>
        <NavLink to="/coach/matchs">Matchs</NavLink>
      </nav>
      <div className="shell">
        <Outlet />
      </div>
    </div>
  );
}
