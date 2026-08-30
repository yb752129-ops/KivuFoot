import { Link } from "react-router-dom";
import { useKivu } from "../context.jsx";

export default function Clubs() {
  const { clubs } = useKivu();
  return (
    <section className="hero">
      <div className="kicker">Clubs</div>
      <h1>Équipes</h1>
      <div className="club-grid">
        {clubs.map((c) => (
          <Link key={c.id} to={`/clubs/${c.id}`} className="club-tile">
            <strong>{c.nom}</strong>
            <div className="meta">{c.ville} · {c.stade}</div>
          </Link>
        ))}
      </div>
    </section>
  );
}
