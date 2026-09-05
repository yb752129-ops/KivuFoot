import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { clubName, useKivu } from "../../context.jsx";
import { AVenirLigne } from "../../components/LignesMatch.jsx";
import { groupMatchsByJournee, journeeTitre, stripDemo } from "../../display.js";
import { fmtQuand, STATUT_MATCH } from "../orga/saison.js";

export default function ClubMatchs() {
  const { user } = useAuth();
  const { saison, clubsById } = useKivu();
  const clubId = user?.club_id;
  const [matchs, setMatchs] = useState([]);

  useEffect(() => {
    if (!saison || !clubId) {
      setMatchs([]);
      return;
    }
    api.matchs(saison.id).then((list) => {
      setMatchs((list || []).filter((m) => m.equipe_domicile_id === clubId || m.equipe_exterieur_id === clubId));
    }).catch(() => setMatchs([]));
  }, [saison, clubId]);

  function nom(id) {
    return stripDemo(clubName(clubsById, id));
  }

  if (!clubId) return <p className="empty">Aucun club rattaché.</p>;

  const groupes = groupMatchsByJournee(matchs);

  return (
    <section className="hero">
      <h1>Matchs</h1>
      <p className="lead">Les matchs de ce club. La saisie reste au collecteur.</p>
      {matchs.length === 0 && <p className="empty">Aucun match.</p>}
      {groupes.map((g) => (
        <div key={g.code} className="journee-block">
          <p className="journee-date">{journeeTitre(g.code)}</p>
          {g.items.map((m) => (
            m.statut === "programme" ? (
              <AVenirLigne key={m.id} match={m} clubsById={clubsById} to={`/matchs/${m.id}`} />
            ) : (
              <Link key={m.id} to={`/matchs/${m.id}`} className="avenir-row termine-row">
                <span className="avenir-noms">
                  <span>{nom(m.equipe_domicile_id)} · {nom(m.equipe_exterieur_id)}</span>
                  <span className="meta-line">{[STATUT_MATCH[m.statut] || m.statut, fmtQuand(m.date_heure)].filter(Boolean).join(" · ")}</span>
                </span>
                <span className="termine-score">{m.score_domicile}–{m.score_exterieur}</span>
              </Link>
            )
          ))}
        </div>
      ))}
    </section>
  );
}
