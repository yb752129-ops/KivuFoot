import { Link } from "react-router-dom";
import { useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";

export default function Clubs() {
  const { clubs, saisonClubs } = useKivu();
  const list = saisonClubs ?? clubs;
  return (
    <section className="hero">
      <h1>Équipes</h1>
      {list.length === 0 && (
        <p className="empty">Aucune équipe inscrite pour le moment. Les noms se complètent à l’organisation.</p>
      )}
      {list.map((c) => (
        <Link key={c.id} to={`/clubs/${c.id}`} className="avenir-row">
          <span className="club-initiale" aria-hidden="true">
            {(stripDemo(c.nom) || "?").charAt(0)}
          </span>
          <span className="avenir-noms">
            <span>{stripDemo(c.nom)}</span>
            <span className="meta-line">{[c.ville, c.stade].filter(Boolean).join(" — ") || "Lieu à compléter"}</span>
          </span>
        </Link>
      ))}
    </section>
  );
}
