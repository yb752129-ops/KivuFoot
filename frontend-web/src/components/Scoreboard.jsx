import { Link } from "react-router-dom";
import { clubName } from "../context.jsx";

function initials(name) {
  return (name || "?")
    .replace(/^DEMO\s+/i, "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(-2)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export default function Scoreboard({ match, clubsById, to }) {
  const home = clubName(clubsById, match.equipe_domicile_id);
  const away = clubName(clubsById, match.equipe_exterieur_id);
  const inner = (
    <>
      <div className="sb-team">
        <span className="crest">{initials(home)}</span>
        <span className="sb-name">{home.replace(/^DEMO\s+/i, "")}</span>
        <span className="meta">{match.journee} · {new Date(match.date_heure).toLocaleDateString("fr-FR")}</span>
      </div>
      <div className="sb-score">{match.score_domicile}–{match.score_exterieur}</div>
      <div className="sb-team right">
        <span className="crest">{initials(away)}</span>
        <span className="sb-name">{away.replace(/^DEMO\s+/i, "")}</span>
        <span className="meta">{match.stade || " "}</span>
      </div>
    </>
  );
  if (to) return <Link to={to} className="scoreboard">{inner}</Link>;
  return <div className="scoreboard">{inner}</div>;
}
