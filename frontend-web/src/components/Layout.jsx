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
            KivuFoot
          </NavLink>
          <nav className="nav">
            <NavLink to="/" end>Accueil</NavLink>
            <NavLink to="/classement">Classement</NavLink>
            <NavLink to="/matchs">Matchs</NavLink>
            <NavLink to="/clubs">Clubs</NavLink>
            <NavLink to="/buteurs">Buteurs</NavLink>
            <NavLink to="/login" className="cta">Organisateur</NavLink>
          </nav>
        </div>
      </header>
      <div className="shell">
        {competition?.est_demo && (
          <div className="banner-demo">
            Prototype — données de démonstration (pas le championnat officiel). Rien n’est publié tant que l’organisateur n’a pas validé.
          </div>
        )}
        {error && <p className="erreur">{error}</p>}
        <Outlet />
        <footer className="site">KivuFoot · football local · Bukavu / Uvira · Sud-Kivu</footer>
      </div>
    </>
  );
}
