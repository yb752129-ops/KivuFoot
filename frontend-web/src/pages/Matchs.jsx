import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import { AVenirLigne, LiveUne, TermineLigne } from "../components/LignesMatch.jsx";
import { dernierFaitLive, groupMatchsByJournee, journeeTitre } from "../display.js";

export default function Matchs() {
  const { saison, clubsById } = useKivu();
  const [matchs, setMatchs] = useState([]);
  const [evtsById, setEvtsById] = useState({});

  useEffect(() => {
    if (!saison) return;
    let stop = false;
    api.matchs(saison.id).then(async (rows) => {
      if (stop) return;
      const list = rows || [];
      setMatchs(list);
      const lives = list.filter((m) => m.statut === "en_cours");
      if (!lives.length) {
        setEvtsById({});
        return;
      }
      const pairs = await Promise.all(
        lives.map((m) =>
          api.evenementsPublics(m.id)
            .then((evts) => [m.id, dernierFaitLive(evts)])
            .catch(() => [m.id, null]),
        ),
      );
      if (!stop) setEvtsById(Object.fromEntries(pairs));
    }).catch(() => setMatchs([]));
    return () => { stop = true; };
  }, [saison]);

  const lives = matchs.filter((m) => m.statut === "en_cours");
  const aVenir = matchs
    .filter((m) => m.statut === "programme")
    .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const termines = matchs
    .filter((m) => m.statut === "termine" || m.statut === "valide")
    .sort((a, b) => new Date(b.date_heure) - new Date(a.date_heure));
  const groupesAvenir = groupMatchsByJournee(aVenir);
  const groupesTermines = groupMatchsByJournee(termines);

  return (
    <section className="hero">
      <h1>Matchs</h1>

      {lives.map((m) => (
        <LiveUne key={m.id} match={m} clubsById={clubsById} evt={evtsById[m.id] || null} />
      ))}

      <div className="section-head">
        <h2>À venir</h2>
      </div>
      {aVenir.length === 0 && <p className="empty">Pas de match programmé.</p>}
      {groupesAvenir.map((g) => (
        <div key={g.code} className="journee-block">
          <p className="journee-date">{journeeTitre(g.code)}</p>
          {g.items.map((m) => (
            <AVenirLigne key={m.id} match={m} clubsById={clubsById} />
          ))}
        </div>
      ))}

      <div className="section-head">
        <h2>Terminés</h2>
      </div>
      {termines.length === 0 && <p className="empty">Pas encore de résultat public.</p>}
      {groupesTermines.map((g) => (
        <div key={g.code} className="journee-block">
          <p className="journee-date">{journeeTitre(g.code)}</p>
          {g.items.map((m) => (
            <TermineLigne key={m.id} match={m} clubsById={clubsById} />
          ))}
        </div>
      ))}
    </section>
  );
}
