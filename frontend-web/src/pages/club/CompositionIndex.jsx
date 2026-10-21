import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { clubName, useKivu } from "../../context.jsx";
import { fmtQuand, STATUT_MATCH } from "../orga/saison.js";
import { stripDemo } from "../../display.js";

export default function ClubCompositionIndex() {
  const { user } = useAuth();
  const { saison, clubsById } = useKivu();
  const [matchs, setMatchs] = useState([]);
  const [erreur, setErreur] = useState("");
  const clubId = user?.club_id;

  useEffect(() => {
    if (!saison || !clubId) {
      setMatchs([]);
      return;
    }
    api.matchs(saison.id)
      .then((rows) => setMatchs((rows || []).filter((m) =>
        m.equipe_domicile_id === clubId || m.equipe_exterieur_id === clubId,
      )))
      .catch((error) => {
        setErreur(error?.message || "Les matchs ne sont pas disponibles.");
        setMatchs([]);
      });
  }, [saison, clubId]);

  if (!clubId) return <p className="empty">Aucun club rattaché.</p>;

  return (
    <section className="hero">
      <p className="kicker">Espace club</p>
      <h1>Compositions</h1>
      <p className="lead">Choisissez un match pour consulter ou préparer la feuille de votre club.</p>
      {erreur && <p className="erreur">{erreur}</p>}
      {matchs.length === 0 && !erreur && <p className="empty">Aucun match pour cette édition.</p>}
      {matchs.map((match) => (
        <Link key={match.id} to={`/club/matchs/${match.id}`} className="avenir-row">
          <span className="avenir-noms">
            <span>
              {stripDemo(clubName(clubsById, match.equipe_domicile_id))} · {stripDemo(clubName(clubsById, match.equipe_exterieur_id))}
            </span>
            <span className="meta-line">
              {[STATUT_MATCH[match.statut] || match.statut, fmtQuand(match.date_heure)].filter(Boolean).join(" · ")}
            </span>
          </span>
          <span className="btn btn-secondary">Ouvrir</span>
        </Link>
      ))}
    </section>
  );
}
