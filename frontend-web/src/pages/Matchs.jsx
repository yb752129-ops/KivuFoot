import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import { AVenirLigne, LiveUne, TermineLigne } from "../components/LignesMatch.jsx";
import { addCivilDays, civilDate, dernierFaitLive, groupMatchsByJournee, journeeTitre, todayCivil } from "../display.js";

export default function Matchs() {
  const { saison, clubsById } = useKivu();
  const [matchs, setMatchs] = useState([]);
  const [dateSelection, setDateSelection] = useState("");
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

  const matchsAffiches = dateSelection
    ? matchs.filter((m) => civilDate(m.date_heure) === dateSelection)
    : matchs;
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
      <div className="calendar-nav" aria-label="Navigation temporelle">
        <button className="btn" type="button" onClick={() => setDateSelection(addCivilDays(dateSelection || todayCivil(), -1))}>← Hier</button>
        <button className={`btn${!dateSelection ? " btn-primary" : ""}`} type="button" onClick={() => setDateSelection("")}>Toutes les dates</button>
        <button className="btn" type="button" onClick={() => setDateSelection(todayCivil())}>Aujourd'hui</button>
        <button className="btn" type="button" onClick={() => setDateSelection(addCivilDays(dateSelection || todayCivil(), 1))}>Demain →</button>
        <label className="field calendar-date-field">
          Date
          <input type="date" value={dateSelection} onChange={(event) => setDateSelection(event.target.value)} />
        </label>
      </div>
      {dateSelection && <p className="journee-date">Matchs du {new Date(`${dateSelection}T12:00:00`).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}</p>}

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
