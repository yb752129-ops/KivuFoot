import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Chrono from "../components/Chrono.jsx";
import { useKivu } from "../context.jsx";
import Scoreboard from "../components/Scoreboard.jsx";
import FeuilleApercu from "../components/FeuilleApercu.jsx";
import Terrain from "../components/Terrain.jsx";
import { formatJour, grouperFaits, journeeTitre, periodeLabel, statsDesFaits, stripDemo } from "../display.js";

const ONGLETS = [
  { id: "apercu", label: "Aperçu" },
  { id: "stats", label: "Statistiques" },
  { id: "compo", label: "Compositions" },
];

export default function MatchDetail() {
  const { id } = useParams();
  const { clubsById, competition } = useKivu();
  const [match, setMatch] = useState(null);
  const [evts, setEvts] = useState([]);
  const [joueurs, setJoueurs] = useState({});
  const [parts, setParts] = useState([]);
  const [onglet, setOnglet] = useState("apercu");
  const [err, setErr] = useState("");

  async function load() {
    const m = await api.match(id);
    const [e, js, p] = await Promise.all([
      api.evenementsPublics(id).catch(() => []),
      api.joueurs().catch(() => []),
      api.participations(id).catch(() => []),
    ]);
    setErr("");
    setMatch(m);
    setEvts(e || []);
    setJoueurs(Object.fromEntries((js || []).map((j) => [j.id, j])));
    setParts(p || []);
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
  const nom = (jid) => joueurs[jid]?.nom_complet || "à compléter";
  const faits = grouperFaits(evts);
  const stats = statsDesFaits(evts);

  return (
    <section className="hero">
      <p className="kicker"><Link to={live ? "/" : "/matchs"}>{live ? "← Accueil" : "← Matchs"}</Link></p>
      {competition?.nom && <p className="kicker">{stripDemo(competition.nom)}</p>}
      {live && (
        <>
          <p className="live-now on-paper">
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
      <div className="sheet mc-score" style={{ marginTop: "0.85rem" }}>
        <Scoreboard match={match} clubsById={clubsById} />
      </div>
      {match.statut === "valide" && <p className="stamp">Validé</p>}
      {match.forfait && <p className="lead">Forfait</p>}

      <div className="mc-tabs" role="tablist">
        {ONGLETS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={onglet === t.id}
            className={onglet === t.id ? "on" : ""}
            onClick={() => setOnglet(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {onglet === "apercu" && (
        <FeuilleApercu faits={faits} nom={nom} match={match} />
      )}

      {onglet === "stats" && (
        <table className="table stats-feuille">
          <thead>
            <tr>
              <th>{stripDemo(home?.nom) || "Domicile"}</th>
              <th />
              <th>{stripDemo(away?.nom) || "Extérieur"}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{match.score_domicile}</td>
              <td>Buts</td>
              <td>{match.score_exterieur}</td>
            </tr>
            <tr>
              <td>{stats.domicile.jaunes}</td>
              <td>Jaunes</td>
              <td>{stats.exterieur.jaunes}</td>
            </tr>
            <tr>
              <td>{stats.domicile.rouges}</td>
              <td>Rouges</td>
              <td>{stats.exterieur.rouges}</td>
            </tr>
            <tr>
              <td>{stats.domicile.penalties_rates}</td>
              <td>Penalties ratés</td>
              <td>{stats.exterieur.penalties_rates}</td>
            </tr>
            <tr>
              <td>—</td>
              <td>Possession</td>
              <td>—</td>
            </tr>
          </tbody>
        </table>
      )}

      {onglet === "compo" && (
        <Terrain
          home={stripDemo(home?.nom)}
          away={stripDemo(away?.nom)}
          parts={parts}
          nom={nom}
          byId={joueurs}
        />
      )}
    </section>
  );
}
