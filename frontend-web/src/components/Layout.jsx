import { NavLink, Outlet } from "react-router-dom";
import { useKivu } from "../context.jsx";

export default function Layout() {
  const { competition, error } = useKivu();
  return (
    <>
      <header className="masthead">
        <div className="masthead-inner">
          <NavLink to="/" className="wordmark">
            <span className="wordmark-name">KivuFoot</span>
            <span className="wordmark-place">Sud-Kivu</span>
          </NavLink>
          {competition?.est_demo && (
            <p className="demo-line">Données de démonstration</p>
          )}
        </div>
      </header>
      <div className="shell">
        {error && <p className="erreur">{error}</p>}
        <Outlet />
        <footer className="site">
          <NavLink to="/login" className="orga-entry">
            Espace organisateur →
          </NavLink>
        </footer>
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
