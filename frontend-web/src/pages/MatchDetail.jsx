import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import Scoreboard from "../components/Scoreboard.jsx";
import { formatJour, journeeTitre, stripDemo } from "../display.js";

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
    let stop = false;
    (async () => {
      try {
        const m = await api.match(id);
        if (stop) return;
        setMatch(m);
        const [e, js] = await Promise.all([
          api.evenementsPublics(id).catch(() => []),
          api.joueurs().catch(() => []),
        ]);
        if (stop) return;
        setEvts(e || []);
        setJoueurs(Object.fromEntries((js || []).map((j) => [j.id, j.nom_complet])));
      } catch (e) {
        if (!stop) setErr(e.message || "Match introuvable.");
      }
    })();
    return () => {
      stop = true;
    };
  }, [id]);

  if (err) {
    return (
      <section className="hero">
        <p className="kicker"><Link to="/matchs">← Matchs</Link></p>
        <p className="erreur">{err}</p>
      </section>
    );
  }
  if (!match) return <p className="empty">Chargement…</p>;

  const home = clubsById[match.equipe_domicile_id];
  const away = clubsById[match.equipe_exterieur_id];

  return (
    <section className="hero">
      <p className="kicker"><Link to="/matchs">← Matchs</Link></p>
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
      {evts.length === 0 && (
        <p className="empty">Aucun événement rendu public pour ce match.</p>
      )}
      <ul className="timeline">
        {evts.map((e) => (
          <li key={e.id}>
            <strong>{e.minute}′</strong>
            {" · "}
            {LABELS[e.type] || e.type}
            {" · "}
            {joueurs[e.joueur_id] || "Joueur"}
          </li>
        ))}
      </ul>
      <p className="id-out">
        {home && <Link to={`/clubs/${match.equipe_domicile_id}`}>{stripDemo(home.nom)}</Link>}
        {home && away && " · "}
        {away && <Link to={`/clubs/${match.equipe_exterieur_id}`}>{stripDemo(away.nom)}</Link>}
      </p>
    </section>
  );
}
