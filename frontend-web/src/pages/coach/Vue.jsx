import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { useKivu } from "../../context.jsx";
import { stripDemo } from "../../display.js";

export default function CoachVue() {
  const { user } = useAuth();
  const { saison } = useKivu();
  const clubId = user?.club_id;
  const [club, setClub] = useState(null);
  const [joueurs, setJoueurs] = useState([]);
  const [matchs, setMatchs] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!clubId) return;
    api.club(clubId).then(setClub).catch((e) => setErr(e.message));
    api.joueurs(clubId).then(setJoueurs).catch(() => setJoueurs([]));
  }, [clubId]);

  useEffect(() => {
    if (!saison || !clubId) {
      setMatchs([]);
      return;
    }
    api.matchs(saison.id).then((list) => {
      setMatchs((list || []).filter((m) => m.equipe_domicile_id === clubId || m.equipe_exterieur_id === clubId));
    }).catch(() => setMatchs([]));
  }, [saison, clubId]);

  if (!clubId) {
    return (
      <section className="hero">
        <h1>Coach</h1>
        <p className="empty">Aucun club rattaché à ce compte.</p>
      </section>
    );
  }

  const nProg = matchs.filter((m) => m.statut === "programme").length;
  const coachNom = user?.nom_complet || club?.coach_nom || "à compléter";

  return (
    <section className="hero">
      <p className="kicker">Coach</p>
      <h1>{club ? stripDemo(club.nom) : "Club"}</h1>
      <p className="lead">La composition de vos matchs. L’effectif reste au club. La saisie reste au collecteur.</p>
      {err && <p className="erreur">{err}</p>}
      <div className="sheet id-sheet">
        <div className="id-row"><span>Ville</span><strong>{club?.ville || "à compléter"}</strong></div>
        <div className="id-row"><span>Stade</span><strong>{club?.stade || "à compléter"}</strong></div>
        <div className="id-row"><span>Coach</span><strong>{coachNom}</strong></div>
        <div className="id-row"><span>Effectif</span><strong>{joueurs.length} joueurs</strong></div>
      </div>
      <div className="orga-chiffres">
        <Link to="/coach/matchs" className="orga-chiffre">
          <strong>{nProg}</strong>
          <span>À venir</span>
        </Link>
        <Link to="/coach/matchs" className="orga-chiffre">
          <strong>{joueurs.length}</strong>
          <span>Joueurs</span>
        </Link>
      </div>
    </section>
  );
}
