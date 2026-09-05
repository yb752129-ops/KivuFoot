import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { clubName, useKivu } from "../context.jsx";
import { labelPoste, stripDemo } from "../display.js";

export default function Joueur() {
  const { id } = useParams();
  const { clubsById } = useKivu();
  const [j, setJ] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.joueur(id).then(setJ).catch((e) => setErr(e.message));
  }, [id]);

  if (err) return <p className="erreur">{err}</p>;
  if (!j) return <p className="empty">Chargement…</p>;

  const club = j.club_actuel_id ? stripDemo(clubName(clubsById, j.club_actuel_id)) : "";

  return (
    <section className="hero">
      <p className="kicker">
        {j.club_actuel_id ? <Link to={`/clubs/${j.club_actuel_id}`}>← {club || "Équipe"}</Link> : <Link to="/clubs">← Équipes</Link>}
      </p>
      <div className="id-head">
        <span className="id-mark" aria-hidden="true">{(j.nom_complet || "?").charAt(0)}</span>
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
        <div className="id-row">
          <span>Numéro</span>
          <strong>à compléter</strong>
        </div>
      </div>
      <p className="empty">Buts, passes et cartons s’affichent après les matchs validés. On n’invente pas de stats.</p>
    </section>
  );
}
