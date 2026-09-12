import { useEffect, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { clubName, useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";
import { IcoBouclier, IcoCalendrier, IcoClassement, IcoCloche, IcoHome, IcoPersonne } from "../icons.jsx";
import Chrono from "./Chrono.jsx";
import Marque from "./Marque.jsx";

const SOMMAIRE = [
  { to: "/", label: "Accueil", end: true, Icon: IcoHome },
  { to: "/matchs", label: "Matchs", Icon: IcoCalendrier },
  { to: "/classement", label: "Classement", Icon: IcoClassement },
  { to: "/clubs", label: "Clubs", Icon: IcoBouclier },
];

function RechercheChamp() {
  return (
    <form className="mast-search" role="search" action="/recherche" method="get">
      <input
        type="search"
        name="q"
        placeholder="Rechercher sur KivuFoot"
        aria-label="Rechercher sur KivuFoot"
      />
    </form>
  );
}

function Cloche() {
  const { saison, clubsById } = useKivu();
  const [open, setOpen] = useState(false);
  const [lives, setLives] = useState([]);

  useEffect(() => {
    if (!saison) return undefined;
    let stop = false;
    function charge() {
      api.matchs(saison.id)
        .then((rows) => {
          if (!stop) setLives((rows || []).filter((m) => m.statut === "en_cours"));
        })
        .catch(() => { if (!stop) setLives([]); });
    }
    charge();
    const t = setInterval(charge, 30000);
    return () => { stop = true; clearInterval(t); };
  }, [saison]);

  return (
    <div className="cloche-wrap">
      <button
        type="button"
        className="mast-round"
        aria-label={lives.length ? `Matchs en direct : ${lives.length}` : "Matchs en direct"}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <IcoCloche className="round-ico" />
        {lives.length > 0 && <span className="cloche-badge">{lives.length}</span>}
      </button>
      {open && (
        <div className="cloche-panel" role="dialog" aria-label="Matchs en direct">
          <p className="cloche-titre">En direct</p>
          {lives.length === 0 && <p className="cloche-vide">Aucun match en direct.</p>}
          {lives.map((m) => (
            <Link
              key={m.id}
              to={`/matchs/${m.id}`}
              className="cloche-ligne"
              onClick={() => setOpen(false)}
            >
              <Chrono match={m} running />
              <span>
                {stripDemo(clubName(clubsById, m.equipe_domicile_id))} – {stripDemo(clubName(clubsById, m.equipe_exterieur_id))}
              </span>
              <b>{m.score_domicile}–{m.score_exterieur}</b>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Layout() {
  const { competition, competitions, choisirCompetition, error } = useKivu();
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
            <Cloche />
            <NavLink
              to="/compte"
              className="compte-personne"
              aria-label={prenom ? `Compte ${prenom}` : "Compte"}
            >
              <IcoPersonne className="compte-ico" />
            </NavLink>
          </div>
          {competitions.length > 0 && (
            <p className="comp-nom">
              {competition
                ? competition.est_demo
                  ? `Démo — ${stripDemo(competition.nom)}`
                  : stripDemo(competition.nom)
                : ""}
            </p>
          )}
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
