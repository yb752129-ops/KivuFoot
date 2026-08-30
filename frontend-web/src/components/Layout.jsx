import { NavLink, Outlet } from "react-router-dom";
import { useKivu } from "../context.jsx";

export default function Layout() {
  const { competition, error } = useKivu();
  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand">
            <span className="brand-mark">KF</span>
            <span>
              KivuFoot
              <small>SUD-KIVU</small>
            </span>
          </NavLink>
          <NavLink to="/login" className="btn-orga">Organisateur</NavLink>
        </div>
      </header>
      <div className="shell">
        {competition?.est_demo && (
          <div className="banner-demo">
            Prototype — clubs et scores de démonstration. Rien n’est officiel tant que l’organisateur n’a pas validé.
          </div>
        )}
        {error && <p className="erreur">{error}</p>}
        <Outlet />
        <footer className="site">Infrastructure du football local · Bukavu / Uvira</footer>
      </div>
      <nav className="bottom-nav">
        <NavLink to="/" end>Accueil</NavLink>
        <NavLink to="/classement">Classement</NavLink>
        <NavLink to="/matchs">Matchs</NavLink>
        <NavLink to="/clubs">Clubs</NavLink>
        <NavLink to="/buteurs">Buteurs</NavLink>
      </nav>
    </>
  );
}
