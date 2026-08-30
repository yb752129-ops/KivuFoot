import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import Scoreboard from "../components/Scoreboard.jsx";

export default function Home() {
  const { loading, saison, clubsById, competition } = useKivu();
  const [classement, setClassement] = useState([]);
  const [matchs, setMatchs] = useState([]);

  useEffect(() => {
    if (!saison) return;
    api.classement(saison.id).then(setClassement).catch(() => setClassement([]));
    api.matchs(saison.id).then(setMatchs).catch(() => setMatchs([]));
  }, [saison]);

  if (loading) return <p className="empty">Chargement du championnat…</p>;
  const titre = (competition?.nom || "KivuFoot").replace(/^DEMO\s*-\s*/i, "");

  return (
    <>
      <section className="hero">
        <div className="kicker">Sud-Kivu · football local</div>
        <h1>{titre}</h1>
        <p className="lead">
          Résultats officiels et classement. Une donnée n’apparaît ici qu’après validation de l’organisateur.
        </p>
      </section>

      <article className="card">
        <h2>Dernière journée</h2>
        {matchs.length === 0 && <p className="empty">Aucun match publié.</p>}
        {matchs.slice(0, 6).map((m) => (
          <Scoreboard key={m.id} match={m} clubsById={clubsById} to={`/matchs/${m.id}`} />
        ))}
      </article>

      <article className="card">
        <h2>Classement</h2>
        {classement.length === 0 && <p className="empty">Le classement se calcule sur les matchs validés.</p>}
        {classement.length > 0 && (
          <table className="table">
            <thead>
              <tr><th>#</th><th>Club</th><th>Pts</th><th>J</th><th>Diff</th></tr>
            </thead>
            <tbody>
              {classement.map((l, i) => (
                <tr key={l.club_id}>
                  <td className="pos">{i + 1}</td>
                  <td><Link to={`/clubs/${l.club_id}`}>{l.club_nom.replace(/^DEMO\s+/i, "")}</Link></td>
                  <td><strong>{l.points}</strong></td>
                  <td>{l.matchs_joues}</td>
                  <td>{l.difference_buts > 0 ? `+${l.difference_buts}` : l.difference_buts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="meta" style={{ marginTop: "0.9rem" }}><Link to="/classement">Tableau complet →</Link></p>
      </article>
    </>
  );
}
