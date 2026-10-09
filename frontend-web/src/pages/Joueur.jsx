import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { clubName, useKivu } from "../context.jsx";
import { labelPoste, stripDemo } from "../display.js";

const LIGNES_STATS = [
  ["Matchs", "matchs_joues"],
  ["Titularisations", "titularisations"],
  ["Minutes", "minutes_jouees"],
  ["Buts", "buts"],
  ["Passes décisives", "passes_decisives"],
  ["Cartons jaunes", "cartons_jaunes"],
  ["Cartons rouges", "cartons_rouges"],
  ["Penalties marqués", "penalties_marques"],
  ["Penalties ratés", "penalties_rates"],
  ["Homme du match", "hommes_du_match"],
];

const STATUTS = {
  CONFIRMEE: "Confirmées",
  PROVISOIRE: "Provisoires",
  NON_DISPONIBLE: "Non disponibles",
};

function valeurStatistique(valeur) {
  // Un zéro réellement agrégé reste un zéro. Seules les valeurs absentes
  // sont présentées comme indisponibles.
  return valeur === null || valeur === undefined ? "Non disponible" : valeur;
}

function dateMatch(dateHeure) {
  if (!dateHeure) return "Date indisponible";
  const date = new Date(dateHeure);
  if (Number.isNaN(date.getTime())) return "Date indisponible";
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short" })
    .format(date)
    .replace(".", "");
}

function faitsIndividuels(match) {
  const stats = match.statistiques || {};
  const faits = [];
  if (stats.buts > 0) faits.push(`${stats.buts} but${stats.buts > 1 ? "s" : ""}`);
  if (stats.passes_decisives > 0) {
    faits.push(`${stats.passes_decisives} passe${stats.passes_decisives > 1 ? "s" : ""}`);
  }
  if (stats.penalties_marques > 0) faits.push(`${stats.penalties_marques} penalty${stats.penalties_marques > 1 ? "s" : ""} marqué${stats.penalties_marques > 1 ? "s" : ""}`);
  if (stats.penalties_rates > 0) faits.push(`${stats.penalties_rates} penalty${stats.penalties_rates > 1 ? "s" : ""} raté${stats.penalties_rates > 1 ? "s" : ""}`);
  if (stats.cartons_jaunes > 0) faits.push(`${stats.cartons_jaunes} jaune${stats.cartons_jaunes > 1 ? "s" : ""}`);
  if (stats.cartons_rouges > 0) faits.push(`${stats.cartons_rouges} rouge${stats.cartons_rouges > 1 ? "s" : ""}`);
  if (match.homme_du_match === true) faits.push("Homme du match");
  return faits;
}

function scoreMatch(match) {
  if (match.score_equipe === null || match.score_equipe === undefined || match.score_adversaire === null || match.score_adversaire === undefined) {
    return "Score indisponible";
  }
  return `${match.score_equipe} – ${match.score_adversaire}`;
}

export default function Joueur() {
  const { id } = useParams();
  const { clubsById, saison } = useKivu();
  const [j, setJ] = useState(null);
  const [stats, setStats] = useState(null);
  const [matchHistory, setMatchHistory] = useState(null);

  const [err, setErr] = useState("");

  useEffect(() => {
    api.joueur(id).then(setJ).catch((e) => setErr(e.message));
  }, [id]);

  useEffect(() => {
    if (!saison) {
      setStats(null);
      setMatchHistory(null);
      return;
    }
    api.statistiquesJoueurPublic(id, saison.id).then(setStats).catch(() => setStats(null));
    api.matchsJoueurPublic(id, saison.id).then(setMatchHistory).catch(() => setMatchHistory(null));
  }, [id, saison]);

  if (err) return <p className="erreur">{err}</p>;
  if (!j) return <p className="empty">Chargement…</p>;

  const club = j.club_actuel_id ? stripDemo(clubName(clubsById, j.club_actuel_id)) : "";
  const statut = stats?.statut || "NON_DISPONIBLE";
  const statutLabel = STATUTS[statut] || "État non précisé";
  const sourceLabel = stats?.source === "matchs_officiellement_valides"
    ? "Matchs officiellement validés"
    : "Aucune source confirmée";

  return (
    <section className="hero">
      <p className="kicker">
        {j.club_actuel_id ? <Link to={`/clubs/${j.club_actuel_id}`}>← {club || "Équipe"}</Link> : <Link to="/clubs">← Équipes</Link>}
      </p>
      <div className="id-head">
        <span className="id-mark" aria-hidden="true">
          {j.photo_url ? <img src={j.photo_url} alt="" className="id-mark-photo" /> : (j.nom_complet || "?").charAt(0)}
        </span>
        <div>
          <h1>{j.nom_complet}</h1>
          <p className="journee-date">{labelPoste(j.poste) || "Poste à compléter"}</p>
        </div>
      </div>
      <div className="sheet id-sheet">
        <div className="id-row">
          <span>Équipe</span>
          <strong>
            {j.club_actuel_id ? (
              <Link to={`/clubs/${j.club_actuel_id}`}>{club || "à compléter"}</Link>
            ) : "à compléter"}
          </strong>
        </div>
        <div className="id-row">
          <span>Poste</span>
          <strong>{labelPoste(j.poste) || "à compléter"}</strong>
        </div>
      </div>
      <div className="section-head">
        <h2>Performance par édition</h2>
        {saison?.nom && <span className="section-note">{saison.nom}</span>}
      </div>
      {!stats ? (
        <p className="empty">Statistiques non disponibles pour cette édition.</p>
      ) : (
        <>
          <div className={`performance-status performance-status-${statut.toLowerCase()}`}>
            <div className="performance-status-top">
              <span className="status-pill">{statutLabel}</span>
              <span className="performance-source">Source : {sourceLabel}</span>
            </div>
            <p>{stats.message || "État de validation non précisé."}</p>
          </div>
          <div className="sheet id-sheet">
            {LIGNES_STATS.map(([label, cle]) => (
              <div className="id-row" key={cle}>
                <span>{label}</span>
                <strong className={stats[cle] === null || stats[cle] === undefined ? "stat-unavailable" : ""}>
                  {valeurStatistique(stats[cle])}
                </strong>
              </div>
            ))}
          </div>
          {stats.donnees_non_collectees?.length > 0 && (
            <div className="performance-note">
              <strong>Données non collectées</strong>
              <p>{stats.donnees_non_collectees.join(" · ")}</p>
            </div>
          )}
          <p className="muted small">Un zéro indique une valeur mesurée nulle ; « Non disponible » indique qu’aucune donnée fiable n’est publiée.</p>
        </>
      )}
      <div className="section-head player-match-section-head">
        <h2>Matchs validés</h2>
        {matchHistory?.matchs?.length > 0 && (
          <span className="section-note">{matchHistory.matchs.length} match{matchHistory.matchs.length > 1 ? "s" : ""}</span>
        )}
      </div>
      {!matchHistory ? (
        <p className="empty">Historique des matchs non disponible pour cette édition.</p>
      ) : matchHistory.matchs?.length === 0 ? (
        <div className="performance-status performance-status-non_disponible">
          <span className="status-pill">Non disponibles</span>
          <p>{matchHistory.message || "Aucun match officiellement validé pour cette édition."}</p>
        </div>
      ) : (
        <div className="player-match-list">
          {matchHistory.matchs.map((match) => {
            const participation = match.participation || {};
            const faits = faitsIndividuels(match);
            return (
              <article className="player-match-card" key={match.match_id}>
                <div className="player-match-header">
                  <div>
                    <span className="player-match-date">{dateMatch(match.date_heure)}</span>
                    <strong>{match.journee || "Match validé"}</strong>
                  </div>
                  <span className="status-pill">Confirmé</span>
                </div>
                <div className="player-match-scoreline">
                  <div>
                    <strong>{match.club_nom || "Équipe non précisée"}</strong>
                    <span>contre {match.adversaire_nom || "Adversaire non précisé"}</span>
                  </div>
                  <b>{scoreMatch(match)}</b>
                </div>
                <div className="player-match-details">
                  <span>{participation.disponible ? (participation.titulaire ? "Titulaire" : "Remplaçant") : "Participation non disponible"}</span>
                  <span>{participation.minutes === null || participation.minutes === undefined ? "Minutes non disponibles" : `${participation.minutes} min`}</span>
                </div>
                {faits.length > 0 ? (
                  <p className="player-match-facts">{faits.join(" · ")}</p>
                ) : participation.disponible ? (
                  <p className="player-match-facts player-match-facts-muted">Aucun fait individuel enregistré</p>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
