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

export default function Joueur() {
  const { id } = useParams();
  const { clubsById, saison } = useKivu();
  const [j, setJ] = useState(null);
  const [stats, setStats] = useState(null);

  const [err, setErr] = useState("");

  useEffect(() => {
    api.joueur(id).then(setJ).catch((e) => setErr(e.message));
  }, [id]);

  useEffect(() => {
    if (!saison) {
      setStats(null);
      return;
    }
    api.statistiquesJoueurPublic(id, saison.id).then(setStats).catch(() => setStats(null));
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
    </section>
  );
}
