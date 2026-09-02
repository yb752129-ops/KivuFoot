import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { clubName, useKivu } from "../context.jsx";
import Scoreboard from "../components/Scoreboard.jsx";
import { formatJour, groupMatchsByJournee, journeeTitre, stripDemo } from "../display.js";

const EVT = {
  but: "But",
  but_contre_son_camp: "CSC",
  passe_decisive: "Passe",
  carton_jaune: "Jaune",
  carton_rouge: "Rouge",
  remplacement: "Changement",
  penalty: "Penalty",
};

function nomClub(clubsById, id) {
  return stripDemo(clubName(clubsById, id));
}

function LiveUne({ match, clubsById, evt }) {
  const home = nomClub(clubsById, match.equipe_domicile_id);
  const away = nomClub(clubsById, match.equipe_exterieur_id);
  const sd = match.score_domicile;
  const se = match.score_exterieur;
  const minute = evt?.minute;
  const cote =
    evt?.equipe_concernee === "exterieur" ? away : evt ? home : "";
  return (
    <>
    <style>{`
      .live-dot{position:relative;width:12px;height:12px;flex:0 0 auto}
      .live-dot b{display:block;width:12px;height:12px;border-radius:50%;background:#e31c1c;animation:live-beat .9s ease-in-out infinite}
      .live-dot::after{content:"";position:absolute;inset:-4px;border-radius:50%;border:2px solid #e31c1c;animation:live-ping .9s ease-out infinite}
      @keyframes live-beat{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(.72);opacity:.55}}
      @keyframes live-ping{0%{transform:scale(.6);opacity:.9}100%{transform:scale(1.8);opacity:0}}
      .live-band .sb-score,.live-band .sb-name{color:#f3efe4}
    `}</style>
    <Link
      to={`/matchs/${match.id}`}
      className="live-band"
      style={{
        display: "block",
        background: "#1f4d36",
        color: "#f3efe4",
        margin: "0 -1rem 0.4rem",
        padding: "1rem 1rem 1.2rem",
      }}
    >
      <p className="live-now">
        <span className="live-dot" aria-hidden="true"><b /></span>
        En cours
      </p>
      {minute != null && <p className="live-min">{minute}′</p>}
      <div className="sb-line">
        <span className="sb-name">{home}</span>
        <span className="sb-score">
          {sd}
          <span className="sb-dash">–</span>
          {se}
        </span>
        <span className="sb-name away">{away}</span>
      </div>
        {evt && (
        <p className="live-evt">
          {minute}′ · {EVT[evt.type] || evt.type}
          {cote ? ` · ${cote}` : ""}
        </p>
      )}
    </Link>
    </>
  );
}

export default function Home() {
  const { loading, saison, clubsById, competition } = useKivu();
  const [classement, setClassement] = useState([]);
  const [matchs, setMatchs] = useState([]);
  const [evt, setEvt] = useState(null);

  useEffect(() => {
    if (!saison) return;
    api.classement(saison.id).then(setClassement).catch(() => setClassement([]));
    api.matchs(saison.id).then(setMatchs).catch(() => setMatchs([]));
  }, [saison]);

  const last = groupMatchsByJournee(matchs)[0];
  const items = last?.items || [];
  const live =
    matchs.find((m) => m.statut === "en_cours") ||
    (competition?.est_demo ? items[0] : null) ||
    null;
  const rest = live ? items.filter((m) => m.id !== live.id) : items;

  useEffect(() => {
    if (!live?.id) {
      setEvt(null);
      return;
    }
    let stop = false;
    api.evenementsPublics(live.id)
      .then((list) => {
        if (stop) return;
        const sorted = [...(list || [])].sort((a, b) => (b.minute || 0) - (a.minute || 0));
        setEvt(sorted[0] || null);
      })
      .catch(() => {
        if (!stop) setEvt(null);
      });
    return () => {
      stop = true;
    };
  }, [live?.id]);

  if (loading) return <p className="empty">Chargement…</p>;

  const enTete = [stripDemo(competition?.nom || ""), saison?.nom]
    .filter(Boolean)
    .join(" — ");

  return (
    <>
      {live && <LiveUne match={live} clubsById={clubsById} evt={evt} />}

      {!live && (
        <section>
          {enTete && <p className="comp-head">{enTete}</p>}
          <h1>{items.length ? journeeTitre(last.code) : "Aucun match publié"}</h1>
          {last?.date && <p className="journee-date">{formatJour(last.date, true)}</p>}
          {items.length === 0 && <p className="empty">Aucun résultat public pour le moment.</p>}
          {items.length > 0 && (
            <div className="sheet">
              {items.map((m) => (
                <Scoreboard key={m.id} match={m} clubsById={clubsById} to={`/matchs/${m.id}`} />
              ))}
            </div>
          )}
        </section>
      )}

      {live && rest.length > 0 && (
        <section>
          <div className="section-head">
            <h2>Terminé</h2>
          </div>
          <div className="sheet">
            {rest.map((m) => (
              <Scoreboard key={m.id} match={m} clubsById={clubsById} to={`/matchs/${m.id}`} />
            ))}
          </div>
        </section>
      )}

      <section>
        <div className="section-head">
          <h2>Classement</h2>
          <Link to="/classement">Tableau complet</Link>
        </div>
        {classement.length === 0 && (
          <p className="empty">Le classement se calcule sur les matchs validés.</p>
        )}
        {classement.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Club</th>
                <th>Pts</th>
                <th>J</th>
                <th>Diff</th>
              </tr>
            </thead>
            <tbody>
              {classement.map((l, i) => (
                <tr key={l.club_id}>
                  <td className="pos">{i + 1}</td>
                  <td>
                    <Link to={`/clubs/${l.club_id}`}>{stripDemo(l.club_nom)}</Link>
                  </td>
                  <td><strong>{l.points}</strong></td>
                  <td>{l.matchs_joues}</td>
                  <td>
                    {l.difference_buts > 0 ? `+${l.difference_buts}` : l.difference_buts}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
