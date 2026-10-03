import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { clubName, useKivu } from "../context.jsx";
import { labelPoste, stripDemo } from "../display.js";

export default function Joueur() {
  const { id } = useParams();
  const { clubsById, saison } = useKivu();
  const [j, setJ] = useState(null);
  const [stats, setStats] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.joueur(id).then(setJ).catch((e) => setErr(e.message));
  }, [id]);

  useEffect(() => {
    if (!saison) {
      setStats(null);
      setDocuments([]);
      return;
    }
    api.statistiquesJoueurPublic(id, saison.id).then(setStats).catch(() => setStats(null));
    api.documentsJoueur(id, saison.id).then(setDocuments).catch(() => setDocuments([]));
  }, [id, saison]);

  if (err) return <p className="erreur">{err}</p>;
  if (!j) return <p className="empty">Chargement…</p>;

  const club = j.club_actuel_id ? stripDemo(clubName(clubsById, j.club_actuel_id)) : "";

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
        <h2>Statistiques officielles</h2>
      </div>
      {!stats ? (
        <p className="empty">Statistiques non disponibles pour cette édition.</p>
      ) : (
        <>
          <div className="sheet id-sheet">
            {[
              ["Matchs", stats.matchs_joues],
              ["Titularisations", stats.titularisations],
              ["Minutes", stats.minutes_jouees],
              ["Buts", stats.buts],
              ["Passes décisives", stats.passes_decisives],
              ["Cartons jaunes", stats.cartons_jaunes],
              ["Cartons rouges", stats.cartons_rouges],
              ["Penalties marqués", stats.penalties_marques],
              ["Penalties ratés", stats.penalties_rates],
              ["Homme du match", stats.hommes_du_match],
            ].map(([label, valeur]) => (
              <div className="id-row" key={label}>
                <span>{label}</span>
                <strong>{valeur ?? 0}</strong>
              </div>
            ))}
          </div>
          <p className="muted small">Statistiques calculées à partir des matchs officiellement validés.</p>
          {documents.map((document) => document.url && (
            <a className="btn" key={document.id} href={document.url} target="_blank" rel="noreferrer">
              Télécharger la fiche PDF officielle
            </a>
          ))}
        </>
      )}
    </section>
  );
}
