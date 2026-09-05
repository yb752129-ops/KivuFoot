import { NavLink, Outlet, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";

export default function CollecteurLayout() {
  const nav = useNavigate();
  const { logout } = useAuth();
  const { competition } = useKivu();
  const nom = competition ? stripDemo(competition.nom) : "Aucune compétition";

  async function out() {
    await logout();
    nav("/", { replace: true });
  }

  return (
    <div className="orga-app collecteur-app">
      <header className="orga-top">
        <div className="orga-top-inner">
          <Link to="/" className="wordmark-name">KivuFoot</Link>
          <p className="orga-comp">{nom}</p>
          <button className="linkish" type="button" onClick={out}>
            Déconnexion
          </button>
        </div>
      </header>
      <nav className="orga-nav" aria-label="Collecte">
        <NavLink to="/collecteur" end>Matchs</NavLink>
      </nav>
      <div className="shell">
        <Outlet />
      </div>
    </div>
  );
}
