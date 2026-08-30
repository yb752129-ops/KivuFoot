import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";

export default function Buteurs() {
  const { saison } = useKivu();
  const [buteurs, setButeurs] = useState([]);
  const [passeurs, setPasseurs] = useState([]);

  useEffect(() => {
    if (!saison) return;
    api.buteurs(saison.id).then(setButeurs).catch(() => setButeurs([]));
    api.passeurs(saison.id).then(setPasseurs).catch(() => setPasseurs([]));
  }, [saison]);

  return (
    <section className="hero">
      <div className="kicker">Stats publiques</div>
      <h1>Buteurs &amp; passeurs</h1>
      <div className="grid grid-2">
        <article className="card">
          <h2>Meilleurs buteurs</h2>
          {buteurs.length === 0 && <p className="empty">Pas encore de stats (elles se remplissent à la validation des événements).</p>}
          <ol className="timeline">
            {buteurs.map((b) => (
              <li key={b.joueur_id}>
                <Link to={`/joueurs/${b.joueur_id}`}><strong>{b.joueur_nom}</strong></Link> · {b.valeur}
              </li>
            ))}
          </ol>
        </article>
        <article className="card">
          <h2>Meilleurs passeurs</h2>
          {passeurs.length === 0 && <p className="empty">Pas encore de passes décisives validées.</p>}
          <ol className="timeline">
            {passeurs.map((b) => (
              <li key={b.joueur_id}>
                <Link to={`/joueurs/${b.joueur_id}`}><strong>{b.joueur_nom}</strong></Link> · {b.valeur}
              </li>
            ))}
          </ol>
        </article>
      </div>
    </section>
  );
}
