import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import Scoreboard from "../components/Scoreboard.jsx";

function stripDemo(name) {
  return (name || "").replace(/^DEMO\s*[-–]?\s*/i, "").trim();
}

function journeeTitre(code) {
  const m = String(code || "").match(/(\d+)/);
  return m ? `Journée ${m[1]}` : "Dernière journée";
}

function derniereJournee(matchs) {
  if (!matchs.length) return { code: null, date: null, items: [] };
  const latest = [...matchs].sort(
    (a, b) => new Date(b.date_heure) - new Date(a.date_heure)
  )[0];
  const items = matchs
    .filter((m) => m.journee === latest.journee)
    .sort((a, b) => a.id - b.id);
  return { code: latest.journee, date: latest.date_heure, items };
}

export default function Home() {
  const { loading, saison, clubsById, competition } = useKivu();
  const [classement, setClassement] = useState([]);
  const [matchs, setMatchs] = useState([]);

  useEffect(() => {
    if (!saison) return;
    api.classement(saison.id).then(setClassement).catch(() => setClassement([]));
    api.matchs(saison.id).then(setMatchs).catch(() => setMatchs([]));
  }, [saison]);

  if (loading) return <p className="empty">Chargement…</p>;

  const { code, date, items } = derniereJournee(matchs);
  const dateLabel = date
    ? new Date(date).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "";
  const titreComp = stripDemo(competition?.nom || "");

  return (
    <>
      <section>
        {titreComp && <p className="comp-name">{titreComp}</p>}
        <h1>{items.length ? journeeTitre(code) : "Aucun match publié"}</h1>
        {dateLabel && <p className="journee-date">{dateLabel}</p>}

        {items.length === 0 && <p className="empty">Aucun résultat public pour le moment.</p>}
        {items.length > 0 && (
          <div className="sheet">
            {items.map((m) => (
              <Scoreboard key={m.id} match={m} clubsById={clubsById} to={`/matchs/${m.id}`} />
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="section-head">
          <h2>Classement</h2>
          <Link to="/classement">Tableau complet</Link>
        </div>
        {classement.length === 0 && (
          <p className="empty">Le classement se calcule sur les matchs validés.</p>
        )}
        {classement.length > 0 && (
          <table className="table">
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
              {classement.map((l, i) => (
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
      </section>
    </>
  );
}
