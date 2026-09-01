import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { useKivu } from "../context.jsx";

export default function Layout() {
  const { competition, error } = useKivu();
  const { prenom } = useAuth();
  return (
    <>
      <header className="masthead">
        <div className="masthead-inner">
          <div className="masthead-row">
            <NavLink to="/" className="wordmark">
              <span className="wordmark-name">KivuFoot</span>
              <span className="wordmark-place">Sud-Kivu</span>
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
      <nav className="bottom-nav">
        <NavLink to="/" end>Accueil</NavLink>
        <NavLink to="/matchs">Matchs</NavLink>
        <NavLink to="/classement">Classement</NavLink>
        <NavLink to="/clubs">Clubs</NavLink>
      </nav>
    </>
  );
}
