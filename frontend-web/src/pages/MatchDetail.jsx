import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Chrono from "../components/Chrono.jsx";
import { useKivu } from "../context.jsx";
import Scoreboard from "../components/Scoreboard.jsx";
import FaitMatch from "../components/FaitMatch.jsx";
import { formatJour, grouperFaits, journeeTitre, periodeLabel, stripDemo } from "../display.js";

export default function MatchDetail() {
  const { id } = useParams();
  const { clubsById, competition } = useKivu();
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
  const faits = grouperFaits(evts).sort(
    (a, b) =>
      (b.minute || 0) - (a.minute || 0)
      || (b.minute_additionnelle || 0) - (a.minute_additionnelle || 0)
      || b.id - a.id,
  );

  return (
    <section className="hero">
      <p className="kicker"><Link to={live ? "/" : "/matchs"}>{live ? "← Accueil" : "← Matchs"}</Link></p>
      {competition?.nom && <p className="kicker">{stripDemo(competition.nom)}</p>}
      {live && (
        <>
          <p className="live-now">
            <span className="live-dot" aria-hidden="true"><b /></span>
            {match.periode === "mi_temps" ? "Mi-temps" : "En direct"}
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
      <div className="sheet mc-score" style={{ marginTop: "0.85rem" }}>
        <Scoreboard match={match} clubsById={clubsById} />
      </div>
      {match.statut === "valide" && <p className="stamp">Validé</p>}
      {match.forfait && <p className="lead">Forfait</p>}

      <div className="section-head">
        <h2>Match</h2>
      </div>
      {faits.length === 0 && (
        <p className="empty">Aucun événement rendu public pour ce match.</p>
      )}
      <ul className="timeline faits">
        {faits.map((e) => (
          <FaitMatch key={e.id} e={e} nom={(jid) => joueurs[jid] || "Joueur"} />
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
