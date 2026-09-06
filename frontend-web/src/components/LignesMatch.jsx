import { Link } from "react-router-dom";
import { clubName } from "../context.jsx";
import Chrono from "./Chrono.jsx";
import { Carton } from "../icons.jsx";
import {
  formatDateline,
  formatHeure,
  formatMinute,
  journeeTitre,
  labelEvenement,
  periodeLabel,
  stripDemo,
} from "../display.js";

export function nomClub(clubsById, id) {
  return stripDemo(clubName(clubsById, id));
}

function Chevron() {
  return (
    <svg className="bulletin-chevron" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 5.5 16 12 9 18.5" />
    </svg>
  );
}

export function LiveUne({ match, clubsById, evt }) {
  const home = nomClub(clubsById, match.equipe_domicile_id);
  const away = nomClub(clubsById, match.equipe_exterieur_id);
  const sd = match.score_domicile;
  const se = match.score_exterieur;
  const cote = evt?.equipe_concernee === "exterieur" ? away : evt ? home : "";
  const journee = match.journee ? journeeTitre(match.journee) : "";
  const periode = periodeLabel(match.periode);
  const carton = evt?.type === "carton_rouge" ? "rouge" : evt?.type === "carton_jaune" ? "jaune" : "";
  return (
    <Link to={`/matchs/${match.id}`} className="live-band">
      <p className="live-now">
        <span className="live-dot" aria-hidden="true"><b /></span>
        {match.periode === "mi_temps" ? "Mi-temps" : "En cours"}
      </p>
      {(journee || periode) && (
        <p className="live-kicker">
          {[journee, periode].filter(Boolean).join(" · ")}
        </p>
      )}
      <div className="live-body">
        <Chrono match={match} running={match.periode !== "mi_temps"} />
        <div className="live-center">
          <p className="live-team">{home || "Équipe à nommer"}</p>
          <p className="live-score">
            {sd}
            <span className="sb-dash">–</span>
            {se}
          </p>
          <p className="live-team">{away || "Équipe à nommer"}</p>
        </div>
      </div>
      {evt && (
        <p className="live-evt">
          {carton && <Carton couleur={carton} />}
          {formatMinute(evt.minute, evt.minute_additionnelle)} · {labelEvenement(evt)}
          {cote ? ` · ${cote}` : ""}
        </p>
      )}
    </Link>
  );
}

export function AVenirLigne({ match, clubsById, to }) {
  const home = nomClub(clubsById, match.equipe_domicile_id);
  const away = nomClub(clubsById, match.equipe_exterieur_id);
  const lieu = formatDateline(match.date_heure, match.stade);
  return (
    <Link to={to || `/matchs/${match.id}`} className="bulletin-row">
      <span className="bulletin-quand">
        <span className="bulletin-etat">À venir</span>
        <span className="bulletin-heure">{formatHeure(match.date_heure)}</span>
      </span>
      <span className="bulletin-noms">
        <span>{home || "Équipe à nommer"}</span>
        <span>{away || "Équipe à nommer"}</span>
        {lieu && <span className="bulletin-lieu">{lieu}</span>}
      </span>
      <Chevron />
    </Link>
  );
}

export function TermineLigne({ match, clubsById, to }) {
  const home = nomClub(clubsById, match.equipe_domicile_id);
  const away = nomClub(clubsById, match.equipe_exterieur_id);
  const officiel = match.statut === "valide";
  return (
    <Link to={to || `/matchs/${match.id}`} className="bulletin-row">
      <span className="bulletin-quand">
        <span className="bulletin-etat">{officiel ? "Validé" : "Terminé"}</span>
        <span className="bulletin-heure">{formatHeure(match.date_heure)}</span>
      </span>
      <span className="bulletin-noms">
        <span>{home || "Équipe à nommer"}</span>
        <span>{away || "Équipe à nommer"}</span>
        {officiel && <span className="bulletin-lieu">Résultat officiel</span>}
      </span>
      <span className="bulletin-score">
        {match.score_domicile}–{match.score_exterieur}
      </span>
    </Link>
  );
}
