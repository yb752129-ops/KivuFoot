import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { stripDemo } from "../display.js";
import { useKivu } from "../context.jsx";

function initiales(nom) {
  return String(nom || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((mot) => mot.charAt(0))
    .join("")
    .toUpperCase();
}

function JoueurStatRow({ ligne }) {
  const nom = ligne.joueur_nom || `Joueur #${ligne.joueur_id}`;
  const club = ligne.club_nom ? stripDemo(ligne.club_nom) : "Équipe à compléter";
  return (
    <Link
      to={`/joueurs/${ligne.joueur_id}`}
      className="stats-joueur-row"
      aria-label={`${nom}, ${club}, ${ligne.valeur}`}
    >
      <span className="stats-joueur-photo" aria-hidden="true">
        {ligne.photo_url ? <img src={ligne.photo_url} alt="" loading="lazy" /> : initiales(nom)}
      </span>
      <span className="stats-joueur-infos">
        <strong>{nom}</strong>
        <span>{club}</span>
      </span>
      <strong className="termine-score">{ligne.valeur}</strong>
    </Link>
  );
}

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
      {buteurs.map((ligne) => <JoueurStatRow key={ligne.joueur_id} ligne={ligne} />)}
      <div className="section-head">
        <h2>Passes décisives</h2>
      </div>
      {passeurs.length === 0 && <p className="empty">Pas encore de passes décisives validées.</p>}
      {passeurs.map((ligne) => <JoueurStatRow key={ligne.joueur_id} ligne={ligne} />)}
    </section>
  );
}
