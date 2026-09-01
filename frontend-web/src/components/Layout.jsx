import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { useKivu } from "../context.jsx";
import Sceau from "./Sceau.jsx";

const SOMMAIRE = [
  { to: "/", label: "Accueil", end: true },
  { to: "/matchs", label: "Matchs" },
  { to: "/classement", label: "Classement" },
  { to: "/clubs", label: "Clubs" },
];

export default function Layout() {
  const { competition, error } = useKivu();
  const { prenom } = useAuth();
  return (
    <>
      <header className="masthead">
        <div className="masthead-inner">
          <div className="masthead-row">
            <NavLink to="/" className="wordmark">
              <span className="wordmark-lockup">
                <Sceau className="brand-sceau" />
                <span className="wordmark-col">
                  <span className="wordmark-name">KivuFoot</span>
                  <span className="wordmark-place">Sud-Kivu</span>
                </span>
              </span>
            </NavLink>
            <NavLink to="/compte" className="compte-link">
              {prenom || "Compte"}
            </NavLink>
          </div>
          {competition?.est_demo && (
            <p className="demo-line">Données de démonstration</p>
          )}
        </div>
      </header>
      <div className="shell">
        {error && <p className="erreur">{error}</p>}
        <Outlet />
      </div>
      <nav className="bottom-nav" aria-label="Sommaire">
        {SOMMAIRE.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}>
            {({ isActive }) => (
              <>
                {isActive && <Sceau className="nav-sceau" />}
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
