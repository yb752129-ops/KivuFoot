import { Link } from "react-router-dom";
import { clubName } from "../context.jsx";
import Chrono from "./Chrono.jsx";
import { formatHeure, formatMinute, labelEvenement, stripDemo } from "../display.js";

export function nomClub(clubsById, id) {
  return stripDemo(clubName(clubsById, id));
}

export function LiveUne({ match, clubsById, evt }) {
  const home = nomClub(clubsById, match.equipe_domicile_id);
  const away = nomClub(clubsById, match.equipe_exterieur_id);
  const sd = match.score_domicile;
  const se = match.score_exterieur;
  const cote = evt?.equipe_concernee === "exterieur" ? away : evt ? home : "";
  return (
    <Link to={`/matchs/${match.id}`} className="live-band">
      <p className="live-now">
        <span className="live-dot" aria-hidden="true"><b /></span>
        {match.periode === "mi_temps" ? "Mi-temps" : "En cours"}
      </p>
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
  return (
    <Link to={to || `/matchs/${match.id}`} className="avenir-row">
      <span className="avenir-heure">{formatHeure(match.date_heure)}</span>
      <span className="avenir-noms">
        <span>{home || "Équipe à nommer"}</span>
        <span>{away || "Équipe à nommer"}</span>
      </span>
    </Link>
  );
}

export function TermineLigne({ match, clubsById, to }) {
  const home = nomClub(clubsById, match.equipe_domicile_id);
  const away = nomClub(clubsById, match.equipe_exterieur_id);
  return (
    <Link to={to || `/matchs/${match.id}`} className="avenir-row termine-row">
      <span className="avenir-heure">{formatHeure(match.date_heure)}</span>
      <span className="avenir-noms">
        <span>{home || "Équipe à nommer"}</span>
        <span>{away || "Équipe à nommer"}</span>
      </span>
      <span className="termine-score">
        {match.score_domicile}–{match.score_exterieur}
      </span>
    </Link>
  );
}
