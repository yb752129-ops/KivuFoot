import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import { AVenirLigne, TermineLigne } from "../components/LignesMatch.jsx";
import { labelPoste, stripDemo } from "../display.js";

export default function ClubDetail() {
  const { id } = useParams();
  const { saison, clubsById } = useKivu();
  const [club, setClub] = useState(null);
  const [joueurs, setJoueurs] = useState([]);
  const [matchs, setMatchs] = useState([]);

  useEffect(() => {
    api.club(id).then(setClub).catch(() => setClub(null));
    api.joueurs(id).then(setJoueurs).catch(() => setJoueurs([]));
  }, [id]);

  useEffect(() => {
    if (!saison) return;
    const cid = Number(id);
    api.matchs(saison.id).then((rows) => {
      setMatchs((rows || []).filter((m) => m.equipe_domicile_id === cid || m.equipe_exterieur_id === cid));
    }).catch(() => setMatchs([]));
  }, [saison, id]);

  if (!club) return <p className="empty">Chargement…</p>;

  const lieu = [club.ville, club.stade].filter(Boolean).join(" — ");
  const aVenir = matchs.filter((m) => m.statut === "programme").sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const termines = matchs
    .filter((m) => m.statut === "termine" || m.statut === "valide")
    .sort((a, b) => new Date(b.date_heure) - new Date(a.date_heure));

  return (
    <section className="hero">
      <p className="kicker"><Link to="/clubs">← Équipes</Link></p>
      <div className="id-head">
        <span className="id-mark" aria-hidden="true">{(stripDemo(club.nom) || "?").charAt(0)}</span>
        <div>
          <h1>{stripDemo(club.nom)}</h1>
          <p className="journee-date">{lieu || "Lieu à compléter"}</p>
        </div>
      </div>
      <p className="lead">Coach · à compléter</p>

      <div className="section-head">
        <h2>Effectif</h2>
      </div>
      {joueurs.length === 0 && (
        <p className="empty">Aucun joueur pour le moment. Noms à compléter au championnat.</p>
      )}
      {joueurs.map((j) => (
        <Link key={j.id} to={`/joueurs/${j.id}`} className="avenir-row">
          <span className="club-initiale" aria-hidden="true">{(j.nom_complet || "?").charAt(0)}</span>
          <span className="avenir-noms">
            <span>{j.nom_complet}</span>
            <span className="meta-line">{labelPoste(j.poste) || "Poste à compléter"}</span>
          </span>
        </Link>
      ))}

      <div className="section-head">
        <h2>À venir</h2>
      </div>
      {aVenir.length === 0 && <p className="empty">Pas de match programmé.</p>}
      {aVenir.map((m) => (
        <AVenirLigne key={m.id} match={m} clubsById={clubsById} />
      ))}

      <div className="section-head">
        <h2>Résultats</h2>
      </div>
      {termines.length === 0 && <p className="empty">Pas encore de résultat public.</p>}
      {termines.map((m) => (
        <TermineLigne key={m.id} match={m} clubsById={clubsById} />
      ))}
    </section>
  );
}
