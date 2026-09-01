import { Link } from "react-router-dom";
import { clubName } from "../context.jsx";
import { formatDateline, journeeTitre } from "../display.js";

function displayName(name) {
  return (name || "").replace(/^DEMO\s*[-–]?\s*/i, "").trim() || name;
}

export default function Scoreboard({ match, clubsById, to }) {
  const home = displayName(clubName(clubsById, match.equipe_domicile_id));
  const away = displayName(clubName(clubsById, match.equipe_exterieur_id));
  const sd = match.score_domicile;
  const se = match.score_exterieur;
  const played = sd != null && se != null;
  const homeWin = played && sd > se;
  const awayWin = played && se > sd;
  const lieu = formatDateline(match.date_heure, match.stade);

  const inner = (
    <>
      <div className="sb-line">
        <span className={`sb-name${homeWin ? " is-winner" : ""}${awayWin ? " is-loser" : ""}`}>
          {home}
        </span>
        <span className="sb-score">
          {played ? (
            <>
              {sd}
              <span className="sb-dash">–</span>
              {se}
            </>
          ) : (
            <span className="sb-dash">–</span>
          )}
        </span>
        <span className={`sb-name away${awayWin ? " is-winner" : ""}${homeWin ? " is-loser" : ""}`}>
          {away}
        </span>
      </div>
      <div className="sb-meta">
        <span className="sb-meta-journee">{journeeTitre(match.journee)}</span>
        {lieu && <span className="sb-meta-lieu">{lieu}</span>}
      </div>
    </>
  );

  if (to) return <Link to={to} className="scoreboard">{inner}</Link>;
  return <div className="scoreboard">{inner}</div>;
}
