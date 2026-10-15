import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { IcoBouclier, IcoCalendrier, IcoClassement, IcoCloche, IcoHome, IcoPersonne, IcoRecherche } from "../icons.jsx";
import Marque from "./Marque.jsx";

const SOMMAIRE = [
  { to: "/", label: "Accueil", end: true, Icon: IcoHome },
  { to: "/matchs", label: "Matchs", Icon: IcoCalendrier },
  { to: "/classement", label: "Classement", Icon: IcoClassement },
  { to: "/clubs", label: "Clubs", Icon: IcoBouclier },
];

function LoadingHeader() {
  return (
    <header className="kf-loading-masthead">
      <div className="kf-public-topbar">
        <span className="kf-public-brand" aria-label="KivuFoot, Sud-Kivu">
          <Marque />
        </span>
        <div className="kf-public-actions" aria-hidden="true">
          <span className="kf-public-action"><IcoRecherche className="round-ico" /></span>
          <span className="kf-public-action"><IcoCloche className="round-ico" /></span>
          <span className="compte-personne"><IcoPersonne className="compte-ico" /></span>
        </div>
      </div>
      <div className="kf-public-edition-bar kf-loading-edition" aria-label="Édition active">
        <span>Chargement…</span>
        <span className="edition-caret" aria-hidden="true">⌄</span>
      </div>
    </header>
  );
}

function LoadingSkeletons() {
  return (
    <>
      <div className="kf-loading-title-block" aria-hidden="true">
        <span className="kf-skeleton kf-skeleton-kicker" />
        <span className="kf-skeleton kf-skeleton-title" />
        <span className="kf-skeleton kf-skeleton-subtitle" />
      </div>
      <section className="kf-loading-cards" aria-hidden="true">
        <article className="kf-loading-card">
          <span className="kf-skeleton kf-skeleton-card-line kf-skeleton-card-line-short" />
          <span className="kf-skeleton kf-skeleton-card-score" />
          <span className="kf-skeleton kf-skeleton-card-line" />
        </article>
        <article className="kf-loading-card">
          <span className="kf-skeleton kf-skeleton-card-line kf-skeleton-card-line-short" />
          <span className="kf-skeleton kf-skeleton-card-score" />
          <span className="kf-skeleton kf-skeleton-card-line" />
        </article>
      </section>
      <section className="kf-loading-ranking" aria-hidden="true">
        <div className="kf-loading-ranking-head">
          <span className="kf-skeleton kf-skeleton-section-title" />
          <span className="kf-skeleton kf-skeleton-section-meta" />
        </div>
        <div className="kf-loading-ranking-columns">
          <span className="kf-skeleton kf-skeleton-column-rank" />
          <span className="kf-skeleton kf-skeleton-column-club" />
          <span className="kf-skeleton kf-skeleton-column-stat" />
          <span className="kf-skeleton kf-skeleton-column-stat" />
        </div>
        {Array.from({ length: 6 }, (_, index) => (
          <div className="kf-loading-ranking-row" key={index}>
            <span className="kf-skeleton kf-skeleton-row-rank" />
            <span className="kf-skeleton kf-skeleton-row-club" />
            <span className="kf-skeleton kf-skeleton-row-stat" />
            <span className="kf-skeleton kf-skeleton-row-stat" />
          </div>
        ))}
      </section>
    </>
  );
}

export default function ChargementEcran({ erreur, onRetry }) {
  const [serveurLent, setServeurLent] = useState(false);
  const fail = Boolean(erreur);

  useEffect(() => {
    if (fail) return undefined;
    const timer = window.setTimeout(() => setServeurLent(true), 8000);
    return () => window.clearTimeout(timer);
  }, [fail]);

  return (
    <div className="kf-public-frame kf-loading-frame">
      <LoadingHeader />
      <main className="kf-loading-main" role="status" aria-live="polite" aria-busy={!fail}>
        <div className="kf-loading-message">
          <p className="kf-loading-status">
            {fail
              ? "Le serveur ne répond pas."
              : serveurLent
                ? "Le serveur démarre, quelques secondes encore…"
                : "Chargement…"}
          </p>
          {fail && erreur && <p className="kf-loading-error">{erreur}</p>}
          {fail && onRetry && (
            <button className="btn btn-primary kf-loading-retry" type="button" onClick={onRetry}>
              Réessayer
            </button>
          )}
        </div>
        <LoadingSkeletons />
      </main>
      <nav className="kf-public-bottom-nav" aria-label="Sommaire">
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
