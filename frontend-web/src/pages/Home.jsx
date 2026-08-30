import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { clubName, useKivu } from "../context.jsx";

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

  return (
    <>
      <section className="hero">
        <div className="kicker">Sud-Kivu · football local</div>
        <h1>{competition?.nom?.replace(/^DEMO - /, "") || "KivuFoot"}</h1>
        <p className="lead">
          Résultats officiels, classement et validation. Ce qui n’est pas validé par l’organisateur
          n’apparaît pas ici.
        </p>
      </section>

      <div className="grid grid-2">
        <article className="card">
          <h2>Derniers matchs publiés</h2>
          {matchs.length === 0 && <p className="empty">Aucun match publié pour l’instant.</p>}
          {matchs.slice(0, 6).map((m) => (
            <Link key={m.id} to={`/matchs/${m.id}`} className="match">
              <div className="team">
                {clubName(clubsById, m.equipe_domicile_id)}
                <div className="meta">{m.journee} · {new Date(m.date_heure).toLocaleDateString("fr-FR")}</div>
              </div>
              <div className="score">{m.score_domicile} – {m.score_exterieur}</div>
              <div className="team right">{clubName(clubsById, m.equipe_exterieur_id)}</div>
            </Link>
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
                    <td><Link to={`/clubs/${l.club_id}`}>{l.club_nom}</Link></td>
                    <td><strong>{l.points}</strong></td>
                    <td>{l.matchs_joues}</td>
                    <td>{l.difference_buts > 0 ? `+${l.difference_buts}` : l.difference_buts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p style={{ marginTop: "0.8rem" }}><Link to="/classement">Voir le classement complet →</Link></p>
        </article>
      </div>
    </>
  );
}
