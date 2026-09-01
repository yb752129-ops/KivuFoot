import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import Scoreboard from "../components/Scoreboard.jsx";
import { formatJour, journeeTitre } from "../display.js";

const LABELS = {
  but: "But",
  but_contre_son_camp: "CSC",
  passe_decisive: "Passe",
  carton_jaune: "Jaune",
  carton_rouge: "Rouge",
  remplacement: "Changement",
  penalty: "Penalty",
};

export default function MatchDetail() {
  const { id } = useParams();
  const { clubsById } = useKivu();
  const [match, setMatch] = useState(null);
  const [evts, setEvts] = useState([]);
  const [joueurs, setJoueurs] = useState({});
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const m = await api.match(id);
        setMatch(m);
        const [e, js] = await Promise.all([
          api.evenementsPublics(id).catch(() => []),
          api.joueurs(),
        ]);
        setEvts(e);
        setJoueurs(Object.fromEntries(js.map((j) => [j.id, j.nom_complet])));
      } catch (e) {
        setErr(e.message);
      }
    })();
  }, [id]);

  if (err) return <p className="erreur">{err}</p>;
  if (!match) return <p className="empty">Chargement…</p>;

  return (
    <section className="hero">
      <p className="kicker">
        {journeeTitre(match.journee)}
        {match.date_heure ? ` · ${formatJour(match.date_heure, true)}` : ""}
      </p>
      <div className="sheet" style={{ marginTop: "0.85rem" }}>
        <Scoreboard match={match} clubsById={clubsById} />
      </div>
      {match.statut === "valide" && <p className="stamp">Validé</p>}
      {match.forfait && <p className="lead">Forfait</p>}

      <div className="section-head">
        <h2>Feuille</h2>
      </div>
      {evts.length === 0 && <p className="empty">Pas d’événements publics sur cette feuille.</p>}
      <ul className="timeline">
        {evts.map((e) => (
          <li key={e.id}>
            <strong>{e.minute}′</strong>
            {" · "}
            {LABELS[e.type] || e.type}
            {" · "}
            {joueurs[e.joueur_id] || "Joueur"}
            {e.equipe_concernee === "domicile" ? " · domicile" : " · extérieur"}
          </li>
        ))}
      </ul>
      <p className="meta" style={{ marginTop: "1.1rem" }}>
        <Link to={`/clubs/${match.equipe_domicile_id}`}>Club domicile</Link>
        {" · "}
        <Link to={`/clubs/${match.equipe_exterieur_id}`}>Club extérieur</Link>
      </p>
    </section>
  );
}
