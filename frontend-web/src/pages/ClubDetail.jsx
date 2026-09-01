import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { stripDemo } from "../display.js";

export default function ClubDetail() {
  const { id } = useParams();
  const [club, setClub] = useState(null);
  const [joueurs, setJoueurs] = useState([]);

  useEffect(() => {
    api.club(id).then(setClub).catch(() => setClub(null));
    api.joueurs(id).then(setJoueurs).catch(() => setJoueurs([]));
  }, [id]);

  if (!club) return <p className="empty">Chargement…</p>;

  const lieu = [club.ville, club.stade].filter(Boolean).join(" — ");

  return (
    <section className="hero">
      <h1>{stripDemo(club.nom)}</h1>
      {lieu && <p className="journee-date">{lieu}</p>}
      <div className="section-head">
        <h2>Effectif</h2>
      </div>
      {joueurs.length === 0 && (
        <p className="empty">Aucun joueur rendu public pour ce club.</p>
      )}
      <ul className="timeline">
        {joueurs.map((j) => (
          <li key={j.id}>
            <Link to={`/joueurs/${j.id}`}><strong>{j.nom_complet}</strong></Link>
            {j.poste ? ` · ${j.poste}` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}
