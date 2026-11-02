import { Link } from "react-router-dom";
import { clubName } from "../context.jsx";
import { findPublicClub, formatPublicKickoff, PublicClubLogo, scorePublicVisible, StatutEquipeBadge } from "./PublicDesign.jsx";
import { scoreTirsAuBut, vainqueurTirsAuBut } from "../tirsAuBut.js";
import { eliminationSportiveDansMatch } from "../phaseFinale.js";

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
  const eliminationSportiveHome = eliminationSportiveDansMatch(match, match.equipe_domicile_id, homeStatus);
  const eliminationSportiveAway = eliminationSportiveDansMatch(match, match.equipe_exterieur_id, awayStatus);
  const sd = match.score_domicile;
  const se = match.score_exterieur;
  const played = scorePublicVisible(match) && sd != null && se != null;
  const upcoming = !scorePublicVisible(match);
  const finished = ["termine", "valide"].includes(match.statut);
  const tirsAuBut = Array.isArray(match.tirs_au_but) ? match.tirs_au_but : [];
  const scoreTirs = scoreTirsAuBut(tirsAuBut);
  const shootoutVisible = played && Number(sd) === Number(se) && tirsAuBut.length > 0;
  const shootoutWinner = shootoutVisible ? vainqueurTirsAuBut(tirsAuBut) : null;
  const shootoutConfirmedWinner = match.statut === "valide" ? shootoutWinner : null;
  const homeWin = played && (sd > se || shootoutConfirmedWinner === "domicile");
  const awayWin = played && (se > sd || shootoutConfirmedWinner === "exterieur");
  const homeQualified = shootoutConfirmedWinner === "domicile"
    && !["disqualifie", "elimine"].includes(String(homeStatus || "actif"));
  const awayQualified = shootoutConfirmedWinner === "exterieur"
    && !["disqualifie", "elimine"].includes(String(awayStatus || "actif"));
  const meta = upcoming ? formatPublicKickoff(match.date_heure) : "";
  const inner = (
    <>
      <div className="sb-line">
        <span className={`sb-name${homeWin ? " is-winner" : ""}${awayWin ? " is-loser" : ""}`}>
          <PublicClubLogo club={homeClub} name={home} statut={homeStatus} className="sb-logo" />
          <span className="sb-team-label">{home}</span>
          <StatutEquipeBadge statut={homeStatus} compact />
          {eliminationSportiveHome && <StatutEquipeBadge statut="elimine" compact sportif />}
          {homeQualified && (
            <span
              className="kf-sport-status-badge is-qualifie"
              aria-label="Qualifié sportivement après les tirs au but"
              title="Qualifié sportivement après un match validé décidé aux tirs au but. Le statut administratif reste prioritaire."
            >
              Qualifié
            </span>
          )}
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
                <span className="sb-score-shootout">t.a.b. {scoreTirs.domicile}–{scoreTirs.exterieur}</span>
              )}
            </>
          ) : (
            <span className="sb-dash">—</span>
          )}
        </span>
        <span className={`sb-name away${awayWin ? " is-winner" : ""}${homeWin ? " is-loser" : ""}`}>
          <PublicClubLogo club={awayClub} name={away} statut={awayStatus} className="sb-logo" />
          <span className="sb-team-label">{away}</span>
          <StatutEquipeBadge statut={awayStatus} compact />
          {eliminationSportiveAway && (
            <span
              className="kf-sport-status-badge is-elimine"
              aria-label="Éliminé sportivement"
              title={`Éliminé sportivement après un match validé de phase ${eliminationSportiveAway.libelle}. Le statut administratif reste inchangé.`}
            >
              ÉLIM.
            </span>
          )}
          {awayQualified && (
            <span
              className="kf-sport-status-badge is-qualifie"
              aria-label="Qualifié sportivement après les tirs au but"
              title="Qualifié sportivement après un match validé décidé aux tirs au but. Le statut administratif reste prioritaire."
            >
              Qualifié
            </span>
          )}
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
          {shootoutConfirmedWinner && (
            <span className="sb-shootout-winner">
              Vainqueur aux tirs au but · <strong>{shootoutConfirmedWinner === "domicile" ? home : away}</strong>
            </span>
          )}
          <span className="sb-finished-pill" aria-label="Match terminé">Terminé</span>
        </div>
      )}
    </>
  );

  if (to) return <Link to={to} className="scoreboard">{inner}</Link>;
  return <div className="scoreboard">{inner}</div>;
}
