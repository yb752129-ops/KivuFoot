import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { clubName, useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";

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

  return (
    <section className="hero">
      <h1>{j.nom_complet}</h1>
      <p className="lead">
        {j.poste || "Poste non renseigné"}
        {j.club_actuel_id ? (
          <>
            {" · "}
            <Link to={`/clubs/${j.club_actuel_id}`}>
              {stripDemo(clubName(clubsById, j.club_actuel_id))}
            </Link>
          </>
        ) : null}
      </p>
    </section>
  );
}
