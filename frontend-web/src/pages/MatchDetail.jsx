import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Chrono from "../components/Chrono.jsx";
import { useKivu } from "../context.jsx";
import Scoreboard from "../components/Scoreboard.jsx";
import { formatJour, formatMinute, journeeTitre, periodeLabel, stripDemo } from "../display.js";

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

  async function load() {
    const m = await api.match(id);
    const [e, js] = await Promise.all([
      api.evenementsPublics(id).catch(() => []),
      api.joueurs().catch(() => []),
    ]);
    setErr("");
    setMatch(m);
    setEvts(e || []);
    setJoueurs(Object.fromEntries((js || []).map((j) => [j.id, j.nom_complet])));
  }

  useEffect(() => {
    let stop = false;
    setErr("");
    setMatch(null);
    (async () => {
      try {
        await load();
      } catch (e) {
        if (!stop) setErr(e.message || "Match introuvable.");
      }
    })();
    const t = setInterval(() => {
      load().catch(() => {});
    }, 5000);
    return () => {
      stop = true;
      clearInterval(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
  const live = match.statut === "en_cours";

  return (
    <section className="hero">
      <p className="kicker"><Link to={live ? "/" : "/matchs"}>{live ? "← Accueil" : "← Matchs"}</Link></p>
      {live && (
        <>
          <p className="live-now">
            <span className="live-dot" aria-hidden="true"><b /></span>
            {match.periode === "mi_temps" ? "Mi-temps" : "En cours"}
          </p>
          {periodeLabel(match.periode) && match.periode !== "mi_temps" && (
            <p className="kicker">{periodeLabel(match.periode)}</p>
          )}
          <Chrono match={match} running={match.periode !== "mi_temps"} endedAt={match.ended_at} />
        </>
      )}
      {!live && (
        <p className="kicker">
          {journeeTitre(match.journee)}
          {match.date_heure ? ` · ${formatJour(match.date_heure, true)}` : ""}
        </p>
      )}
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
