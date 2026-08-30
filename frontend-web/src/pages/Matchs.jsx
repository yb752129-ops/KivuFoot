import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import Scoreboard from "../components/Scoreboard.jsx";

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
          <Scoreboard key={m.id} match={m} clubsById={clubsById} to={`/matchs/${m.id}`} />
        ))}
      </div>
    </section>
  );
}
