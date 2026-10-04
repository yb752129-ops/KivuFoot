import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import { AVenirLigne, LiveUne, TermineLigne } from "../components/LignesMatch.jsx";
import { addCivilDays, civilDate, dernierFaitLive, formatDateNavigation, groupMatchsByJournee, journeeTitre, todayCivil } from "../display.js";

export default function Matchs() {
  const { saison, clubsById } = useKivu();
  const [matchs, setMatchs] = useState([]);
  const [dateSelection, setDateSelection] = useState(() => todayCivil());
  const [evtsById, setEvtsById] = useState({});

  useEffect(() => {
    if (!saison) return;
    let stop = false;
    api.matchs(saison.id).then(async (rows) => {
      if (stop) return;
      const list = rows || [];
      setMatchs(list);
      const lives = list.filter((m) => m.statut === "en_cours" && !m.ended_at);
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

  const matchsAffiches = matchs.filter((m) => civilDate(m.date_heure) === dateSelection);
  const lives = matchs.filter((m) => m.statut === "en_cours" && !m.ended_at);
  const aVenir = matchsAffiches
    .filter((m) => m.statut === "programme")
    .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const termines = matchsAffiches
    .filter((m) => m.statut === "termine" || m.statut === "valide")
    .sort((a, b) => new Date(b.date_heure) - new Date(a.date_heure));
  const groupesAvenir = groupMatchsByJournee(aVenir);
  const groupesTermines = groupMatchsByJournee(termines);
  const PHASES = [
    ["quart", "Quarts de finale"],
    ["demi", "Demi-finales"],
    ["finale", "Finale"],
  ];
  const phases = PHASES.map(([code, titre]) => ({
    code,
    titre,
    items: matchsAffiches
      .filter((m) => m.phase === code)
      .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure)),
  })).filter((p) => p.items.length > 0);

  return (
    <section className="hero">
      <h1>Matchs</h1>
      <div className="date-navigation matchs-date-navigation" aria-label="Choisir la date des matchs">
        <button
          type="button"
          className="date-arrow"
          aria-label="Date précédente"
          onClick={() => setDateSelection(addCivilDays(dateSelection, -1))}
        >‹</button>
        <label className="date-picker-control">
          <span>Matchs du</span>
          <strong>{formatDateNavigation(dateSelection)}</strong>
          <input
            type="date"
            value={dateSelection}
            aria-label="Choisir la date des matchs"
            onChange={(event) => setDateSelection(event.target.value || todayCivil())}
          />
        </label>
        <button
          type="button"
          className="date-arrow"
          aria-label="Date suivante"
          onClick={() => setDateSelection(addCivilDays(dateSelection, 1))}
        >›</button>
      </div>
      <p className="journee-date">Matchs du {formatDateNavigation(dateSelection)}</p>

      {lives.map((m) => (
        <LiveUne key={m.id} match={m} clubsById={clubsById} evt={evtsById[m.id] || null} />
      ))}

      {phases.length > 0 && (
        <div className="section-head">
          <h2>Phase finale</h2>
        </div>
      )}
      {phases.map((p) => (
        <div key={p.code} className="journee-block">
          <p className="journee-date">{p.titre}</p>
          {p.items.map((m) =>
            m.statut === "programme" ? (
              <AVenirLigne key={m.id} match={m} clubsById={clubsById} />
            ) : (
              <TermineLigne key={m.id} match={m} clubsById={clubsById} />
            ),
          )}
        </div>
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
