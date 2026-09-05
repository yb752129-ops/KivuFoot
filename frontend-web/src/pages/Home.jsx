import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { useKivu } from "../context.jsx";
import { AVenirLigne, LiveUne, TermineLigne } from "../components/LignesMatch.jsx";
import {
  addCivilDays,
  civilDate,
  dernierFaitLive,
  stripDemo,
  todayCivil,
} from "../display.js";

function fusionner(a, b) {
  const map = new Map();
  for (const m of a || []) map.set(m.id, m);
  for (const m of b || []) map.set(m.id, m);
  return [...map.values()];
}

export default function Home() {
  const { loading, saison, clubsById } = useKivu();
  const { user } = useAuth();
  const staff = user?.role === "organisateur" || user?.role === "admin";
  const [classement, setClassement] = useState([]);
  const [matchs, setMatchs] = useState([]);
  const [evtsById, setEvtsById] = useState({});
  const [jourOffset, setJourOffset] = useState(0);

  useEffect(() => {
    if (!saison) return;
    let stop = false;
    function refresh() {
      api.classement(saison.id).then((c) => { if (!stop) setClassement(c); }).catch(() => { if (!stop) setClassement([]); });
      const pub = api.matchs(saison.id).catch(() => []);
      const gest = staff ? api.matchsGestion(saison.id).catch(() => []) : Promise.resolve([]);
      Promise.all([pub, gest]).then(async ([p, g]) => {
        if (stop) return;
        const rows = fusionner(p, g);
        setMatchs(rows);
        const lives = rows.filter((m) => m.statut === "en_cours");
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
      });
    }
    refresh();
    const t = setInterval(refresh, 5000);
    return () => {
      stop = true;
      clearInterval(t);
    };
  }, [saison, staff]);

  const lives = matchs.filter((m) => m.statut === "en_cours");
  const jour = jourOffset === 0 ? todayCivil() : addCivilDays(todayCivil(), 1);
  const programmes = matchs
    .filter((m) => m.statut === "programme")
    .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const duJour = programmes.filter((m) => civilDate(m.date_heure) === jour);
  const aVenir = duJour.length ? duJour : (jourOffset === 0 ? programmes : []);
  const termines = matchs
    .filter((m) => (m.statut === "termine" || m.statut === "valide") && civilDate(m.date_heure) === jour)
    .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const apercu = classement.slice(0, 5);

  if (loading) return <p className="empty">Chargement…</p>;

  return (
    <>
      {lives.map((m) => (
        <LiveUne key={m.id} match={m} clubsById={clubsById} evt={evtsById[m.id] || null} />
      ))}

      <section>
        <div className="jour-barre">
          <h2>À venir</h2>
          <div className="jour-nav">
            <button
              type="button"
              aria-label="Aujourd'hui"
              disabled={jourOffset === 0}
              onClick={() => setJourOffset(0)}
            >
              ‹
            </button>
            <span>{jourOffset === 0 ? "Aujourd'hui" : "Demain"}</span>
            <button
              type="button"
              aria-label="Demain"
              disabled={jourOffset === 1}
              onClick={() => setJourOffset(1)}
            >
              ›
            </button>
          </div>
        </div>
        {aVenir.length === 0 && <p className="empty">Pas de match prévu ce jour.</p>}
        {aVenir.map((m) => (
          <AVenirLigne key={m.id} match={m} clubsById={clubsById} />
        ))}
      </section>

      <section>
        <div className="section-head">
          <h2>Terminés</h2>
        </div>
        {termines.length === 0 && <p className="empty">Pas encore de match terminé ce jour.</p>}
        {termines.map((m) => (
          <TermineLigne key={m.id} match={m} clubsById={clubsById} />
        ))}
      </section>

      <section>
        <div className="section-head">
          <h2>Classement</h2>
          <Link to="/classement">Tableau complet</Link>
        </div>
        {classement.length === 0 && (
          <p className="empty">Le classement se calcule sur les matchs validés.</p>
        )}
        {apercu.length > 0 && (
          <table className="table table-accueil">
            <thead>
              <tr>
                <th>#</th>
                <th>Club</th>
                <th>Pts</th>
                <th>J</th>
                <th>Diff</th>
              </tr>
            </thead>
            <tbody>
              {apercu.map((l, i) => (
                <tr key={l.club_id}>
                  <td className="pos">{i + 1}</td>
                  <td>
                    <Link to={`/clubs/${l.club_id}`}>{stripDemo(l.club_nom)}</Link>
                  </td>
                  <td><strong>{l.points}</strong></td>
                  <td>{l.matchs_joues}</td>
                  <td>
                    {l.difference_buts > 0 ? `+${l.difference_buts}` : l.difference_buts}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {classement.length > 0 && (
          <p className="table-more">
            <Link to="/classement">Voir le tableau complet</Link>
          </p>
        )}
      </section>
    </>
  );
}
