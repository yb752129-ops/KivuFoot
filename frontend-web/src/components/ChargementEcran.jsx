import { NavLink } from "react-router-dom";
import { IcoBouclier, IcoCalendrier, IcoClassement, IcoHome, IcoPersonne } from "../icons.jsx";
import Marque from "./Marque.jsx";

const SOMMAIRE = [
  { to: "/", label: "Accueil", end: true, Icon: IcoHome },
  { to: "/matchs", label: "Matchs", Icon: IcoCalendrier },
  { to: "/classement", label: "Classement", Icon: IcoClassement },
  { to: "/clubs", label: "Clubs", Icon: IcoBouclier },
];

function BallonCharge() {
  return (
    <span className="charge-orbite" aria-hidden="true">
      <span className="charge-anneau" />
      <span className="charge-anneau charge-anneau-2" />
      <span className="charge-anneau-spin">
        <span className="charge-point" />
      </span>
      <svg className="charge-ballon-spin" viewBox="0 0 64 64">
        <circle cx="32" cy="32" r="27" fill="#f4f1ea" stroke="#1c1914" strokeWidth="2.2" />
        <polygon points="32,18.2 40.2,24.2 37.1,34.2 26.9,34.2 23.8,24.2" fill="#1f4d36" />
        <path fill="#1f4d36" d="M32 5.4 41.2 9.2 38.2 15.4 32 12.8 25.8 15.4 22.8 9.2Z" />
        <path fill="#1f4d36" d="M53.2 20.4 56.6 29.2 50.2 33.4 45.6 25.6 49.4 18.8Z" />
        <path fill="#1f4d36" d="M46.4 47.2 39.6 56.4 32 53.2 35.4 44.2 42.8 42.6Z" />
        <path fill="#1f4d36" d="M17.6 47.2 21.2 42.6 28.6 44.2 32 53.2 24.4 56.4Z" />
        <path fill="#1f4d36" d="M10.8 20.4 14.6 18.8 18.4 25.6 13.8 33.4 7.4 29.2Z" />
        <g fill="none" stroke="#1c1914" strokeWidth="1.6" strokeLinejoin="round">
          <path d="M32 18.2V12.8" />
          <path d="M40.2 24.2 45.6 25.6" />
          <path d="M37.1 34.2 35.4 44.2" />
          <path d="M26.9 34.2 28.6 44.2" />
          <path d="M23.8 24.2 18.4 25.6" />
        </g>
      </svg>
    </span>
  );
}

export default function ChargementEcran({ erreur, onRetry }) {
  const fail = Boolean(erreur);

  return (
    <div className="charge-app">
      <header className="masthead">
        <div className="masthead-inner">
          <div className="masthead-row">
            <span className="wordmark">
              <Marque />
            </span>
            <form className="mast-search" onSubmit={(e) => e.preventDefault()} role="search">
              <input
                type="search"
                placeholder="Rechercher sur KivuFoot"
                aria-label="Rechercher sur KivuFoot"
                disabled
              />
            </form>
            <span className="compte-personne" aria-hidden="true">
              <IcoPersonne className="compte-ico" />
            </span>
          </div>
        </div>
      </header>

      <div
        className="charge-ecran"
        role="status"
        aria-live="polite"
        aria-busy={!fail}
      >
        <BallonCharge />
        {fail ? (
          <>
            <p className="charge-kicker">Connexion impossible</p>
            <h1 className="charge-titre">Le terrain ne répond pas.</h1>
            <p className="charge-texte">{erreur}</p>
            {onRetry && (
              <button className="btn btn-primary charge-retry" type="button" onClick={onRetry}>
                Réessayer
              </button>
            )}
          </>
        ) : (
          <>
            <p className="visually-hidden">
              Connexion en cours. Le terrain se prépare. Nous synchronisons les scores et les feuilles officielles du championnat.
            </p>
            <p className="charge-kicker">Connexion en cours</p>
            <h1 className="charge-titre">Le terrain se prépare.</h1>
            <p className="charge-texte">
              Nous synchronisons les scores et les feuilles officielles du championnat.
            </p>
            <p className="charge-dots" aria-hidden="true">
              <i /><i /><i />
            </p>
          </>
        )}
      </div>

      <nav className="bottom-nav" aria-label="Sommaire">
        {SOMMAIRE.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}>
            <item.Icon className="nav-ico" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
