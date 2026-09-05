import { Link } from "react-router-dom";
import { useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";

export default function Clubs() {
  const { clubs, saisonClubs } = useKivu();
  const list = saisonClubs ?? clubs;
  return (
    <section className="hero">
      <h1>Équipes</h1>
      {list.length === 0 && <p className="empty">Aucune équipe inscrite pour le moment.</p>}
      {list.length > 0 && (
        <div className="sheet">
          {list.map((c) => (
            <Link key={c.id} to={`/clubs/${c.id}`} className="club-tile">
              <strong>{stripDemo(c.nom)}</strong>
              <span className="meta">
                {[c.ville, c.stade].filter(Boolean).join(" — ")}
              </span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
