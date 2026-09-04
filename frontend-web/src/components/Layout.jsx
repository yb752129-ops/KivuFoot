import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { useKivu } from "../context.jsx";
import { IcoBouclier, IcoCalendrier, IcoClassement, IcoHome, IcoPersonne } from "../icons.jsx";
import Marque from "./Marque.jsx";

const SOMMAIRE = [
  { to: "/", label: "Accueil", end: true, Icon: IcoHome },
  { to: "/matchs", label: "Matchs", Icon: IcoCalendrier },
  { to: "/classement", label: "Classement", Icon: IcoClassement },
  { to: "/clubs", label: "Clubs", Icon: IcoBouclier },
];

function RechercheChamp() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  function go(e) {
    e.preventDefault();
    const t = q.trim();
    if (!t) return;
    navigate(`/recherche?q=${encodeURIComponent(t)}`);
  }
  return (
    <form className="mast-search" onSubmit={go} role="search">
      <input
        type="search"
        name="q"
        placeholder="Rechercher sur KivuFoot"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        aria-label="Rechercher sur KivuFoot"
      />
    </form>
  );
}

export default function Layout() {
  const { competition, error } = useKivu();
  const { prenom } = useAuth();
  return (
    <>
      <header className="masthead">
        <div className="masthead-inner">
          <div className="masthead-row">
            <NavLink to="/" className="wordmark" aria-label="KivuFoot, Sud-Kivu">
              <Marque />
            </NavLink>
            <RechercheChamp />
            <NavLink
              to="/compte"
              className="compte-personne"
              aria-label={prenom ? `Compte ${prenom}` : "Compte"}
            >
              <IcoPersonne className="compte-ico" />
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
            <item.Icon className="nav-ico" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
