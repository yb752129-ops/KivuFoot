import { Link } from "react-router-dom";
import { clubName } from "../context.jsx";
import { formatPublicKickoff, scorePublicVisible } from "./PublicDesign.jsx";
import { formatDateline, journeeTitre } from "../display.js";

function displayName(name) {
  return (name || "").replace(/^DEMO\s*[-–]?\s*/i, "").trim() || name;
}

export default function Scoreboard({ match, clubsById, to }) {
  const home = displayName(clubName(clubsById, match.equipe_domicile_id));
  const away = displayName(clubName(clubsById, match.equipe_exterieur_id));
  const sd = match.score_domicile;
  const se = match.score_exterieur;
  const played = scorePublicVisible(match) && sd != null && se != null;
  const upcoming = !scorePublicVisible(match);
  const homeWin = played && sd > se;
  const awayWin = played && se > sd;
  const lieu = formatDateline(match.date_heure, match.stade);
  const meta = upcoming ? formatPublicKickoff(match.date_heure) : lieu;
  const logoHome = clubsById[match.equipe_domicile_id]?.logo_url;
  const logoAway = clubsById[match.equipe_exterieur_id]?.logo_url;

  const inner = (
    <>
      <div className="sb-line">
        <span className={`sb-name${homeWin ? " is-winner" : ""}${awayWin ? " is-loser" : ""}`}>
          {logoHome && <img className="sb-logo" src={logoHome} alt={`Logo ${home}`} />}
          <span>{home}</span>
        </span>
        <span className="sb-score">
          {played ? (
            <>
              {sd}
              <span className="sb-dash">–</span>
              {se}
            </>
          ) : (
            <span className="sb-dash">—</span>
          )}
        </span>
        <span className={`sb-name away${awayWin ? " is-winner" : ""}${homeWin ? " is-loser" : ""}`}>
          <span>{away}</span>
          {logoAway && <img className="sb-logo" src={logoAway} alt={`Logo ${away}`} />}
        </span>
      </div>
      <div className="sb-meta">
        <span className={`sb-meta-journee${upcoming ? " sb-meta-upcoming" : ""}`}>
          {upcoming ? "À VENIR" : journeeTitre(match.journee)}
        </span>
        {meta && <span className="sb-meta-lieu">{meta}</span>}
      </div>
    </>
  );

  if (to) return <Link to={to} className="scoreboard">{inner}</Link>;
  return <div className="scoreboard">{inner}</div>;
}
