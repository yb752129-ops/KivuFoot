import { Link } from "react-router-dom";
import { useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";
import { PublicClubLogo, StatutEquipeBadge } from "../components/PublicDesign.jsx";

export default function Clubs() {
  const { clubs, saisonClubs, saison } = useKivu();
  const list = saisonClubs ?? clubs;
  return (
    <section className="hero">
      <h1>Équipes</h1>
      {list.length === 0 && (
        <p className="empty">Aucune équipe inscrite pour le moment. Les noms se complètent à l’organisation.</p>
      )}
      {list.map((c) => (
        <Link key={c.id} to={`/clubs/${c.id}${saison?.id ? `?saison_id=${saison.id}` : ""}`} className={`avenir-row${c.statut && c.statut !== "actif" ? " team-status-muted" : ""}`}>
          <PublicClubLogo club={c} name={c.nom} statut={c.statut} className="logo-libre" />
          <span className="avenir-noms">
            <span>{stripDemo(c.nom)} <StatutEquipeBadge statut={c.statut} compact /></span>
            <span className="meta-line">{[c.ville, c.stade].filter(Boolean).join(" — ") || "Lieu à compléter"}</span>
          </span>
        </Link>
      ))}
    </section>
  );
}
