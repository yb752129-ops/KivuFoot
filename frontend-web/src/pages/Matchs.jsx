import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import Scoreboard from "../components/Scoreboard.jsx";
import { formatJour, groupMatchsByJournee, journeeTitre } from "../display.js";

export default function Matchs() {
  const { saison, clubsById } = useKivu();
  const [matchs, setMatchs] = useState([]);

  useEffect(() => {
    if (!saison) return;
    api.matchs(saison.id).then(setMatchs).catch(() => setMatchs([]));
  }, [saison]);

  const groups = groupMatchsByJournee(matchs);

  return (
    <section className="hero">
      <h1>Matchs</h1>
      {groups.length === 0 && <p className="empty">Aucun résultat public.</p>}
      {groups.map((g) => (
        <div key={g.code} className="journee-block">
          <div className="section-head">
            <h2>{journeeTitre(g.code)}</h2>
            <span className="kicker">{formatJour(g.date, true)}</span>
          </div>
          <div className="sheet">
            {g.items.map((m) => (
              <Scoreboard key={m.id} match={m} clubsById={clubsById} to={`/matchs/${m.id}`} />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
