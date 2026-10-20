import { Link } from "react-router-dom";
import { clubName } from "../context.jsx";
import Chrono from "./Chrono.jsx";
import { Ecu, IcoEpingle } from "../icons.jsx";
import {
  formatDateline,
  formatHeure,
  journeeTitre,
  stripDemo,
} from "../display.js";

export function nomClub(clubsById, id) {
  return stripDemo(clubName(clubsById, id));
}

function initiales(nom) {
  const mots = (nom || "").split(/\s+/).filter(Boolean);
  const a = mots[0]?.[0] || "?";
  const b = mots[1]?.[0] || mots[0]?.[1] || "";
  return (a + b).toUpperCase();
}

function SceauDoc() {
  return (
    <svg className="off-ico" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 3h9l4 4v14H6z" />
      <path d="M15 3v4h4" />
      <path d="M9.5 13.5l2 2 3.5-4" />
    </svg>
  );
}

function Chevron() {
  return (
    <svg className="bulletin-chevron" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 5.5 16 12 9 18.5" />
    </svg>
  );
}

export function LiveUne({ match, clubsById }) {
  const home = nomClub(clubsById, match.equipe_domicile_id);
  const away = nomClub(clubsById, match.equipe_exterieur_id);
  const sd = match.score_domicile;
  const se = match.score_exterieur;
  const pause = match.periode === "mi_temps";
  const termine = ["termine", "valide"].includes(match.statut);
  const statut = termine ? "Terminé" : pause ? "MI-TEMPS" : "EN COURS";
  const journee = match.journee ? journeeTitre(match.journee) : "";
  const logoHome = clubsById[match.equipe_domicile_id]?.logo_url;
  const logoAway = clubsById[match.equipe_exterieur_id]?.logo_url;
  const chrono = pause
    ? <span className="live-pause-label">MI-TEMPS</span>
    : match.started_at
      ? <Chrono precision="second" match={match} running={!termine && !match.ended_at && match.statut === "en_cours"} />
      : null;
  return (
    <div className="live-band">
      <div className="lk-top">
        <span className={`live-now${pause ? " is-break" : ""}`}>
          <span className="live-dot" aria-hidden="true"><b /></span>
          {statut}
        </span>
        <span className="lk-journee">{journee}</span>
      </div>
      <div className="lk-body">
        <span className="lk-side">
          {logoHome ? <img className="ecu ecu-img" src={logoHome} alt="" /> : <Ecu className="ecu" initiales={initiales(home)} />}
          <span className="lk-name">{home || "Équipe à nommer"}</span>
        </span>
        <span className="lk-center">
          <p className="live-score">
            {sd}
            <span className="sb-dash">–</span>
            {se}
          </p>
          {chrono}
        </span>
        <span className="lk-side">
          {logoAway ? <img className="ecu ecu-img" src={logoAway} alt="" /> : <Ecu className="ecu" initiales={initiales(away)} />}
          <span className="lk-name">{away || "Équipe à nommer"}</span>
        </span>
      </div>
    </div>
  );
}

export function AVenirLigne({ match, clubsById, to }) {
  const home = nomClub(clubsById, match.equipe_domicile_id);
  const away = nomClub(clubsById, match.equipe_exterieur_id);
  const lieu = formatDateline(match.date_heure, match.stade);
  const logoHome = clubsById[match.equipe_domicile_id]?.logo_url;
  const logoAway = clubsById[match.equipe_exterieur_id]?.logo_url;
  return (
    <Link to={to || `/matchs/${match.id}`} className="bulletin-row">
      <span className="bulletin-quand">
        <span className="bulletin-etat">À venir</span>
        <span className="bulletin-heure">{formatHeure(match.date_heure)}</span>
      </span>
      <span className="bulletin-noms">
        <span className="bulletin-nom">
          {logoHome ? <img className="bulletin-logo" src={logoHome} alt="" /> : <span className="bulletin-logo-vide" />}
          {home || "Équipe à nommer"}
        </span>
        <span className="bulletin-nom">
          {logoAway ? <img className="bulletin-logo" src={logoAway} alt="" /> : <span className="bulletin-logo-vide" />}
          {away || "Équipe à nommer"}
        </span>
        {lieu && <span className="bulletin-lieu"><IcoEpingle className="lieu-ico" />{lieu}</span>}
      </span>
      <Chevron />
    </Link>
  );
}

export function TermineLigne({ match, clubsById, to }) {
  const home = nomClub(clubsById, match.equipe_domicile_id);
  const away = nomClub(clubsById, match.equipe_exterieur_id);
  const officiel = match.statut === "valide";
  const logoHome = clubsById[match.equipe_domicile_id]?.logo_url;
  const logoAway = clubsById[match.equipe_exterieur_id]?.logo_url;
  return (
    <Link to={to || `/matchs/${match.id}`} className="bulletin-row">
      <span className="bulletin-quand">
        <span className="bulletin-etat">{officiel ? "Validé" : "Terminé"}</span>
        <span className="bulletin-heure">{formatHeure(match.date_heure)}</span>
      </span>
      <span className="bulletin-noms">
        <span className="bulletin-nom">
          {logoHome ? <img className="bulletin-logo" src={logoHome} alt="" /> : <span className="bulletin-logo-vide" />}
          {home || "Équipe à nommer"}
        </span>
        <span className="bulletin-nom">
          {logoAway ? <img className="bulletin-logo" src={logoAway} alt="" /> : <span className="bulletin-logo-vide" />}
          {away || "Équipe à nommer"}
        </span>
        {officiel && <span className="bulletin-officiel"><SceauDoc />Résultat officiel</span>}
      </span>
      <span className="bulletin-score">
        {match.score_domicile}–{match.score_exterieur}
        <Chevron />
      </span>
    </Link>
  );
}
