import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { useKivu } from "../../context.jsx";
import { stripDemo } from "../../display.js";

export default function ClubVue() {
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
        <h1>Club</h1>
        <p className="empty">Aucun club rattaché à ce compte.</p>
      </section>
    );
  }

  const nProg = matchs.filter((m) => m.statut === "programme").length;
  const nLive = matchs.filter((m) => m.statut === "en_cours").length;

  return (
    <section className="hero">
      <p className="kicker">Club</p>
      <h1>{club ? stripDemo(club.nom) : "Club"}</h1>
      <p className="lead">L’effectif du club. Le public lit. L’organisateur tient la compétition.</p>
      {err && <p className="erreur">{err}</p>}
      {club && (
        <div className="sheet id-sheet">
          <div className="id-row"><span>Ville</span><strong>{club.ville || "à compléter"}</strong></div>
          <div className="id-row"><span>Stade</span><strong>{club.stade || "à compléter"}</strong></div>
          <div className="id-row"><span>Coach</span><strong>à compléter</strong></div>
        </div>
      )}
      <div className="orga-chiffres">
        <Link to="/club/effectif" className="orga-chiffre">
          <strong>{joueurs.length}</strong>
          <span>Joueurs</span>
        </Link>
        <Link to="/club/matchs" className="orga-chiffre">
          <strong>{nProg}</strong>
          <span>À venir</span>
        </Link>
        <Link to="/club/matchs" className="orga-chiffre">
          <strong>{nLive}</strong>
          <span>En cours</span>
        </Link>
      </div>
    </section>
  );
}
