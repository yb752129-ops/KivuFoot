import { Link } from "react-router-dom";
import { useKivu } from "../context.jsx";

function initials(name) {
  return (name || "?")
    .replace(/^DEMO\s+/i, "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(-2)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export default function Clubs() {
  const { clubs } = useKivu();
  return (
    <section className="hero">
      <div className="kicker">Clubs</div>
      <h1>Équipes</h1>
      <div className="club-grid">
        {clubs.map((c) => (
          <Link key={c.id} to={`/clubs/${c.id}`} className="club-tile">
            <span className="crest">{initials(c.nom)}</span>
            <strong>{c.nom.replace(/^DEMO\s+/i, "")}</strong>
            <div className="meta">{c.ville} · {c.stade}</div>
          </Link>
        ))}
      </div>
    </section>
  );
}
