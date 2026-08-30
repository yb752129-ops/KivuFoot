import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";

export default function Classement() {
  const { saison } = useKivu();
  const [lignes, setLignes] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!saison) return;
    api.classement(saison.id).then(setLignes).catch((e) => setErr(e.message));
  }, [saison]);

  return (
    <section className="hero">
      <div className="kicker">Officiel</div>
      <h1>Classement</h1>
      <p className="lead">Uniquement les matchs validés. Victoire 3 pts · nul 1 · défaite 0.</p>
      {err && <p className="erreur">{err}</p>}
      <div className="card" style={{ overflowX: "auto" }}>
        {lignes.length === 0 && <p className="empty">Pas encore de match publié.</p>}
        {lignes.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>#</th><th>Club</th><th>Pts</th><th>J</th><th>G</th><th>N</th><th>P</th><th>BP</th><th>BC</th><th>Diff</th>
              </tr>
            </thead>
            <tbody>
              {lignes.map((l, i) => (
                <tr key={l.club_id}>
                  <td className="pos">{i + 1}</td>
                  <td><Link to={`/clubs/${l.club_id}`}>{l.club_nom.replace(/^DEMO\s+/i, "")}</Link></td>
                  <td><strong>{l.points}</strong></td>
                  <td>{l.matchs_joues}</td>
                  <td>{l.victoires}</td>
                  <td>{l.nuls}</td>
                  <td>{l.defaites}</td>
                  <td>{l.buts_marques}</td>
                  <td>{l.buts_encaisses}</td>
                  <td>{l.difference_buts > 0 ? `+${l.difference_buts}` : l.difference_buts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
