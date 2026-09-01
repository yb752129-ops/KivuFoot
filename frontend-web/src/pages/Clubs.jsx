import { Link } from "react-router-dom";
import { useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";

export default function Clubs() {
  const { clubs } = useKivu();
  return (
    <section className="hero">
      <h1>Clubs</h1>
      {clubs.length === 0 && <p className="empty">Aucun club public pour le moment.</p>}
      {clubs.length > 0 && (
        <div className="sheet">
          {clubs.map((c) => (
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
