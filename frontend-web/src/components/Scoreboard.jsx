import { Link } from "react-router-dom";
import { clubName } from "../context.jsx";

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
  const date = match.date_heure
    ? new Date(match.date_heure).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "short",
      })
    : "";
  const meta = [match.stade, match.journee, date].filter(Boolean).join(" · ");

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
      {meta && <div className="sb-meta">{meta}</div>}
    </>
  );

  if (to) return <Link to={to} className="scoreboard">{inner}</Link>;
  return <div className="scoreboard">{inner}</div>;
}
