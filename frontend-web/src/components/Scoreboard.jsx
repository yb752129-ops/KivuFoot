import { Link } from "react-router-dom";
import { clubName } from "../context.jsx";
import { findPublicClub, formatPublicKickoff, PublicClubLogo, scorePublicVisible } from "./PublicDesign.jsx";
import { scoreTirsAuBut } from "../tirsAuBut.js";
import { bilanPublicMatch, etatTirsAuBut } from "../resultatPublic.js";

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
  const etatTirs = etatTirsAuBut(match);
  const tirsProvisoires = Boolean(etatTirs?.provisoire);
  // Résultat de CE match (officiel après validation) et situation ACTUELLE des
  // équipes sont deux informations distinctes : voir bilanPublicMatch.
  const bilan = bilanPublicMatch(match, { statutDomicile: homeStatus, statutExterieur: awayStatus });
  const homeWin = played && (sd > se || bilan.vainqueurTirs === "domicile");
  const awayWin = played && (se > sd || bilan.vainqueurTirs === "exterieur");
  const nomCote = (cote) => (cote === "domicile" ? home : away);
  const meta = upcoming ? formatPublicKickoff(match.date_heure) : "";
  const inner = (
    <>
      <div className="sb-line">
        <span className={`sb-name${homeWin ? " is-winner" : ""}${awayWin ? " is-loser" : ""}`}>
          <PublicClubLogo club={homeClub} name={home} statut={homeStatus} className="sb-logo" />
          <span className="sb-team-label">{home}</span>
        </span>
        <span
          className={`sb-score${shootoutVisible ? " has-shootout" : ""}`}
          aria-label={shootoutVisible ? `${sd}–${se} · t.a.b. ${scoreTirs.domicile}–${scoreTirs.exterieur}${tirsProvisoires ? " (provisoire)" : ""}` : undefined}
        >
          {played ? (
            <>
              <span className="sb-score-main">
                {sd}
                <span className="sb-dash">–</span>
                {se}
              </span>
              {shootoutVisible && (
                <>
                  <span className="sb-score-shootout">t.a.b. {scoreTirs.domicile}–{scoreTirs.exterieur}</span>
                  {tirsProvisoires && <span className="sb-shootout-provisoire">provisoire</span>}
                </>
              )}
            </>
          ) : (
            <span className="sb-dash">—</span>
          )}
        </span>
        <span className={`sb-name away${awayWin ? " is-winner" : ""}${homeWin ? " is-loser" : ""}`}>
          <PublicClubLogo club={awayClub} name={away} statut={awayStatus} className="sb-logo" />
          <span className="sb-team-label">{away}</span>
        </span>
      </div>
      {upcoming && (
        <div className="sb-meta">
          <span className="sb-meta-journee sb-meta-upcoming">À VENIR</span>
          <span className="sb-meta-lieu">{meta}</span>
        </div>
      )}
      {finished && (
        <div className="sb-bilan">
          <section className="sb-bilan-bloc" aria-label="Ce match">
            <p className="sb-bilan-titre">Ce match</p>
            <p className={`sb-validation-pill ${bilan.officiel ? "is-officiel" : "is-provisoire"}`}>{bilan.libelle}</p>
            {bilan.vainqueurTirs && (
              <p className="sb-bilan-ligne sb-shootout-winner">
                Vainqueur aux tirs au but · <strong>{nomCote(bilan.vainqueurTirs)}</strong>
              </p>
            )}
            {bilan.consequences.map((consequence) => (
              <p key={`${consequence.cote}-${consequence.type}`} className={`sb-bilan-ligne is-${consequence.type}`}>
                {consequence.type === "qualifie" ? "Qualifié pour la suite" : `Éliminé à ce tour (${consequence.libelle})`}
                {" · "}
                <strong>{nomCote(consequence.cote)}</strong>
              </p>
            ))}
          </section>
          {bilan.situations.length > 0 && (
            <section className="sb-bilan-bloc is-situation" aria-label="Situation actuelle des équipes">
              <p className="sb-bilan-titre">Situation actuelle</p>
              {bilan.situations.map((situation) => (
                <p key={situation.cote} className="sb-bilan-ligne is-statut">
                  {situation.libelle}
                  {" · "}
                  <strong>{nomCote(situation.cote)}</strong>
                </p>
              ))}
              <p className="sb-bilan-note">Statut de l’équipe dans l’édition, indépendant du résultat de ce match.</p>
            </section>
          )}
        </div>
      )}
    </>
  );

  if (to) return <Link to={to} className="scoreboard">{inner}</Link>;
  return <div className="scoreboard">{inner}</div>;
}
