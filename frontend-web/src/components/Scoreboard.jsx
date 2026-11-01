import { Link } from "react-router-dom";
import { clubName } from "../context.jsx";
import { findPublicClub, formatPublicKickoff, PublicClubLogo, scorePublicVisible, StatutEquipeBadge } from "./PublicDesign.jsx";
import { scoreTirsAuBut, vainqueurTirsAuBut } from "../tirsAuBut.js";

function displayName(name) {
  return (name || "").replace(/^DEMO\s*[-–]?\s*/i, "").trim() || name;
}

export default function Scoreboard({ match, clubsById, saisonClubs, to }) {
  const homeClub = findPublicClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const awayClub = findPublicClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const home = displayName(homeClub?.nom || clubName(clubsById, match.equipe_domicile_id));
  const away = displayName(awayClub?.nom || clubName(clubsById, match.equipe_exterieur_id));
  const homeStatus = homeClub?.statut;
  const awayStatus = awayClub?.statut;
  const sd = match.score_domicile;
  const se = match.score_exterieur;
  const played = scorePublicVisible(match) && sd != null && se != null;
  const upcoming = !scorePublicVisible(match);
  const finished = ["termine", "valide"].includes(match.statut);
  const tirsAuBut = Array.isArray(match.tirs_au_but) ? match.tirs_au_but : [];
  const scoreTirs = scoreTirsAuBut(tirsAuBut);
  const shootoutVisible = played && Number(sd) === Number(se) && tirsAuBut.length > 0;
  const shootoutWinner = shootoutVisible ? vainqueurTirsAuBut(tirsAuBut) : null;
  const homeWin = played && (sd > se || shootoutWinner === "domicile");
  const awayWin = played && (se > sd || shootoutWinner === "exterieur");
  const meta = upcoming ? formatPublicKickoff(match.date_heure) : "";
  const inner = (
    <>
      <div className="sb-line">
        <span className={`sb-name${homeWin ? " is-winner" : ""}${awayWin ? " is-loser" : ""}`}>
          <PublicClubLogo club={homeClub} name={home} statut={homeStatus} className="sb-logo" />
          <span>{home}</span>
          <StatutEquipeBadge statut={homeStatus} compact />
        </span>
        <span
          className={`sb-score${shootoutVisible ? " has-shootout" : ""}`}
          aria-label={shootoutVisible ? `${sd}–${se} · t.a.b. ${scoreTirs.domicile}–${scoreTirs.exterieur}` : undefined}
        >
          {played ? (
            <>
              <span className="sb-score-main">
                {sd}
                <span className="sb-dash">–</span>
                {se}
              </span>
              {shootoutVisible && (
                <span className="sb-score-shootout">· t.a.b. {scoreTirs.domicile}–{scoreTirs.exterieur}</span>
              )}
            </>
          ) : (
            <span className="sb-dash">—</span>
          )}
        </span>
        <span className={`sb-name away${awayWin ? " is-winner" : ""}${homeWin ? " is-loser" : ""}`}>
          <PublicClubLogo club={awayClub} name={away} statut={awayStatus} className="sb-logo" />
          <span>{away}</span>
          <StatutEquipeBadge statut={awayStatus} compact />
        </span>
      </div>
      {upcoming && (
        <div className="sb-meta">
          <span className="sb-meta-journee sb-meta-upcoming">À VENIR</span>
          <span className="sb-meta-lieu">{meta}</span>
        </div>
      )}
      {finished && (
        <div className="sb-meta sb-meta-status">
          <span className="sb-finished-pill" aria-label="Match terminé">Terminé</span>
        </div>
      )}
    </>
  );

  if (to) return <Link to={to} className="scoreboard">{inner}</Link>;
  return <div className="scoreboard">{inner}</div>;
}
