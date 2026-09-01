import { Link } from "react-router-dom";
import { useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";

export default function Clubs() {
  const { clubs } = useKivu();
  return (
    <section className="hero">
      <h1>Clubs</h1>
      <div className="sheet">
        {clubs.map((c) => (
          <Link key={c.id} to={`/clubs/${c.id}`} className="club-tile">
            <strong>{stripDemo(c.nom)}</strong>
            <div className="meta">{[c.ville, c.stade].filter(Boolean).join(" · ")}</div>
          </Link>
        ))}
      </div>
    </section>
  );
}
