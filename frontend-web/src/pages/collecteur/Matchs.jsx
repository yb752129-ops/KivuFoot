import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api.js";
import { clubName, useKivu } from "../../context.jsx";
import { AVenirLigne } from "../../components/LignesMatch.jsx";
import { groupMatchsByJournee, journeeTitre, stripDemo } from "../../display.js";
import { fmtQuand, STATUT_MATCH } from "../orga/saison.js";

export default function CollecteurMatchs() {
  const { saison, clubsById } = useKivu();
  const [matchs, setMatchs] = useState([]);

  useEffect(() => {
    if (!saison) {
      setMatchs([]);
      return;
    }
    api.matchs(saison.id).then((list) => {
      const utiles = (list || []).filter((m) =>
        m.statut === "programme" || m.statut === "en_cours" || m.statut === "termine",
      );
      setMatchs(utiles);
    }).catch(() => setMatchs([]));
  }, [saison]);

  function nom(id) {
    return stripDemo(clubName(clubsById, id));
  }

  const groupes = groupMatchsByJournee(matchs);

  return (
    <section className="hero">
      <h1>Matchs</h1>
      <p className="lead">Saisir le match. L’organisateur valide.</p>
      {matchs.length === 0 && <p className="empty">Aucun match à saisir.</p>}
      {groupes.map((g) => (
        <div key={g.code} className="journee-block">
          <p className="journee-date">{journeeTitre(g.code)}</p>
          {g.items.map((m) => (
            m.statut === "programme" ? (
              <AVenirLigne key={m.id} match={m} clubsById={clubsById} to={`/collecteur/matchs/${m.id}`} />
            ) : (
              <Link key={m.id} to={`/collecteur/matchs/${m.id}`} className="avenir-row termine-row">
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
