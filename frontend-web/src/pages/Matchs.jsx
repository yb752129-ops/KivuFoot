import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import { AVenirLigne, LiveUne, TermineLigne } from "../components/LignesMatch.jsx";
import {
  addCivilDays,
  civilDate,
  dernierFaitLive,
  formatDateNavigation,
  groupMatchsByJournee,
  journeeTitre,
  todayCivil,
} from "../display.js";

function datesDuWeekEnd(reference = todayCivil()) {
  const jourSemaine = new Date(`${reference}T12:00:00`).getDay();
  const decalageSamedi = jourSemaine === 6 ? 0 : jourSemaine === 0 ? -1 : 6 - jourSemaine;
  const samedi = addCivilDays(reference, decalageSamedi);
  return [samedi, addCivilDays(samedi, 1)];
}

function groupMatchsByDate(matchs) {
  const map = new Map();
  for (const match of matchs) {
    const date = civilDate(match.date_heure);
    if (!map.has(date)) map.set(date, []);
    map.get(date).push(match);
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, items]) => ({
      date,
      items: [...items].sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure)),
    }));
}

export default function Matchs() {
  const { saison, clubsById } = useKivu();
  const [matchs, setMatchs] = useState([]);
  const [dateSelection, setDateSelection] = useState("");
  const [weekendSelection, setWeekendSelection] = useState(null);
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

  const weekendActif = Array.isArray(weekendSelection);
  const matchsAffiches = weekendActif
    ? matchs.filter((m) => weekendSelection.includes(civilDate(m.date_heure)))
    : dateSelection
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
  const groupesWeekend = groupMatchsByDate(
    matchsAffiches.filter((m) => ["programme", "termine", "valide"].includes(m.statut)),
  );
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

  function toutesLesDates() {
    setDateSelection("");
    setWeekendSelection(null);
  }

  function choisirDate(date) {
    setDateSelection(date);
    setWeekendSelection(null);
  }

  function choisirWeekEnd() {
    setDateSelection("");
    setWeekendSelection(datesDuWeekEnd());
  }

  return (
    <section className="hero">
      <h1>Matchs</h1>
      <div className="calendar-nav" aria-label="Navigation temporelle">
        <button className={`btn${weekendActif ? " btn-primary" : ""}`} type="button" onClick={choisirWeekEnd}>
          Ce week-end
        </button>
        <button className={`btn${!dateSelection && !weekendActif ? " btn-primary" : ""}`} type="button" onClick={toutesLesDates}>
          Toutes les dates
        </button>
        <button className="btn" type="button" onClick={() => choisirDate(todayCivil())}>
          Aujourd'hui
        </button>
        <button className="btn" type="button" onClick={() => choisirDate(addCivilDays(dateSelection || todayCivil(), 1))}>
          Demain →
        </button>
        <label className="field calendar-date-field">
          Date
          <input
            type="date"
            value={dateSelection}
            onChange={(event) => choisirDate(event.target.value)}
          />
        </label>
      </div>
      {weekendActif && (
        <p className="journee-date">
          Week-end du {formatDateNavigation(weekendSelection[0])} au {formatDateNavigation(weekendSelection[1])}
        </p>
      )}
      {dateSelection && !weekendActif && (
        <p className="journee-date">
          Matchs du {formatDateNavigation(dateSelection)}
        </p>
      )}

      {lives.map((m) => (
        <LiveUne key={m.id} match={m} clubsById={clubsById} evt={evtsById[m.id] || null} />
      ))}

      {weekendActif ? (
        <>
          {groupesWeekend.length === 0 && <p className="empty">Aucun match publié ce week-end.</p>}
          {groupesWeekend.map((g) => (
            <div key={g.date} className="journee-block">
              <p className="journee-date">{formatDateNavigation(g.date)}</p>
              {g.items.map((m) => (
                m.statut === "programme" ? (
                  <AVenirLigne key={m.id} match={m} clubsById={clubsById} />
                ) : (
                  <TermineLigne key={m.id} match={m} clubsById={clubsById} />
                )
              ))}
            </div>
          ))}
        </>
      ) : (
        <>
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
        </>
      )}
    </section>
  );
}
