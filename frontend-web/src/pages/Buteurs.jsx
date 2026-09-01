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
      <h1>Buteurs</h1>
      <div className="section-head">
        <h2>Buts</h2>
      </div>
      {buteurs.length === 0 && <p className="empty">Pas encore de buts validés.</p>}
      <ol className="timeline">
        {buteurs.map((b) => (
          <li key={b.joueur_id}>
            <Link to={`/joueurs/${b.joueur_id}`}><strong>{b.joueur_nom}</strong></Link>
            {" · "}
            {b.valeur}
          </li>
        ))}
      </ol>
      <div className="section-head">
        <h2>Passes</h2>
      </div>
      {passeurs.length === 0 && <p className="empty">Pas encore de passes validées.</p>}
      <ol className="timeline">
        {passeurs.map((b) => (
          <li key={b.joueur_id}>
            <Link to={`/joueurs/${b.joueur_id}`}><strong>{b.joueur_nom}</strong></Link>
            {" · "}
            {b.valeur}
          </li>
        ))}
      </ol>
    </section>
  );
}
