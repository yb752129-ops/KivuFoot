import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import Scoreboard from "../components/Scoreboard.jsx";
import { formatJour, groupMatchsByJournee, journeeTitre, stripDemo } from "../display.js";

export default function Home() {
  const { loading, saison, clubsById } = useKivu();
  const [classement, setClassement] = useState([]);
  const [matchs, setMatchs] = useState([]);

  useEffect(() => {
    if (!saison) return;
    api.classement(saison.id).then(setClassement).catch(() => setClassement([]));
    api.matchs(saison.id).then(setMatchs).catch(() => setMatchs([]));
  }, [saison]);

  if (loading) return <p className="empty">Chargement…</p>;

  const last = groupMatchsByJournee(matchs)[0];
  const items = last?.items || [];

  return (
    <>
      <section>
        <h1>{items.length ? journeeTitre(last.code) : "Aucun match publié"}</h1>
        {last?.date && <p className="journee-date">{formatJour(last.date, true)}</p>}

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
