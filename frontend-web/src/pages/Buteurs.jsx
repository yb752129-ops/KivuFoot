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
      <p className="kicker"><Link to="/classement">← Classement</Link></p>
      <h1>Buteurs</h1>
      <div className="section-head">
        <h2>Buts</h2>
      </div>
      {buteurs.length === 0 && <p className="empty">Pas encore de buts validés.</p>}
      {buteurs.map((b) => (
        <Link key={b.joueur_id} to={`/joueurs/${b.joueur_id}`} className="avenir-row">
          <span className="avenir-noms">
            <span>{b.joueur_nom}</span>
          </span>
          <span className="termine-score">{b.valeur}</span>
        </Link>
      ))}
      <div className="section-head">
        <h2>Passes</h2>
      </div>
      {passeurs.length === 0 && <p className="empty">Pas encore de passes validées.</p>}
      {passeurs.map((b) => (
        <Link key={b.joueur_id} to={`/joueurs/${b.joueur_id}`} className="avenir-row">
          <span className="avenir-noms">
            <span>{b.joueur_nom}</span>
          </span>
          <span className="termine-score">{b.valeur}</span>
        </Link>
      ))}
    </section>
  );
}
