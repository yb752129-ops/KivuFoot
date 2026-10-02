import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { stripDemo } from "../display.js";

export default function Competition() {
  const { id } = useParams();
  const [competition, setCompetition] = useState(null);
  const [saisons, setSaisons] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    let stop = false;
    setErr("");
    Promise.all([api.competition(id), api.saisons(id)])
      .then(([comp, rows]) => {
        if (stop) return;
        setCompetition(comp);
        setSaisons(rows || []);
      })
      .catch((e) => {
        if (!stop) setErr(e.message);
      });
    return () => { stop = true; };
  }, [id]);

  if (err) {
    return (
      <section className="hero competition-page">
        <p className="kicker"><Link to="/actualites">← Actualités</Link></p>
        <p className="erreur">{err}</p>
      </section>
    );
  }
  if (!competition) return <p className="empty">Chargement de la compétition…</p>;

  return (
    <section className="hero competition-page">
      <p className="kicker"><Link to="/actualites">← Actualités</Link></p>
      <p className="competition-sceau">Compétition officielle</p>
      <h1>{stripDemo(competition.nom)}</h1>
      <p className="lead">{competition.saison_label || "Édition officielle"}</p>
      <div className="competition-fiche">
        <p><strong>Statut</strong><span>{competition.est_active ? "Compétition active" : "Compétition archivée"}</span></p>
        <p><strong>Édition</strong><span>{saisons[0]?.nom || competition.saison_label || "À préciser"}</span></p>
      </div>
      <div className="competition-actions">
        <Link className="btn btn-primary" to={`/actualites?competition_id=${competition.id}`}>Actualités de cette compétition</Link>
        <Link className="btn" to="/classement">Classement</Link>
        <Link className="btn" to="/matchs">Matchs</Link>
      </div>
      <p className="competition-note">
        Cette page présente la compétition concernée. Les communications officielles sont diffusées par KivuFoot,
        sans que KivuFoot ne se substitue au Comité d’Organisation.
      </p>
    </section>
  );
}
