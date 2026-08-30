import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { clubName, useKivu } from "../context.jsx";

export default function Matchs() {
  const { saison, clubsById } = useKivu();
  const [matchs, setMatchs] = useState([]);

  useEffect(() => {
    if (!saison) return;
    api.matchs(saison.id).then(setMatchs).catch(() => setMatchs([]));
  }, [saison]);

  return (
    <section className="hero">
      <div className="kicker">Résultats</div>
      <h1>Matchs publiés</h1>
      <div className="card">
        {matchs.length === 0 && <p className="empty">Aucun résultat public.</p>}
        {matchs.map((m) => (
          <Link key={m.id} to={`/matchs/${m.id}`} className="match">
            <div className="team">
              {clubName(clubsById, m.equipe_domicile_id)}
              <div className="meta">{m.journee} · {m.stade} · {new Date(m.date_heure).toLocaleString("fr-FR")}</div>
            </div>
            <div className="score">{m.score_domicile} – {m.score_exterieur}</div>
            <div className="team right">{clubName(clubsById, m.equipe_exterieur_id)}</div>
          </Link>
        ))}
      </div>
    </section>
  );
}
