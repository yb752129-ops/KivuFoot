import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";

function dateTexte(value) {
  if (!value) return "Date non renseignée";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function statutTexte(value) {
  return {
    en_course: "En course",
    qualifie: "Qualifié",
    non_qualifie: "Non qualifié",
    elimine: "Non qualifié",
    indetermine: "Indéterminé",
  }[value] || value || "Indéterminé";
}

export default function Historique() {
  const { saison } = useKivu();
  const [progression, setProgression] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [records, setRecords] = useState([]);
  const [historique, setHistorique] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!saison) return undefined;
    let stop = false;
    Promise.all([
      api.progressionSaison(saison.id),
      api.timelineSaison(saison.id),
      api.records(saison.id),
      api.historiquePublic(saison.id),
    ]).then(([nextProgression, nextTimeline, nextRecords, nextHistorique]) => {
      if (stop) return;
      setProgression(nextProgression);
      setTimeline(nextTimeline || []);
      setRecords(nextRecords || []);
      setHistorique(nextHistorique || []);
      setErr("");
    }).catch((error) => {
      if (!stop) setErr(error.message || "Impossible de charger l’historique officiel.");
    });
    return () => { stop = true; };
  }, [saison?.id]);

  if (!saison) return <section className="hero"><p className="empty">Aucune édition sélectionnée.</p></section>;

  return (
    <section className="hero historique-page">
      <p className="kicker">Archives officielles</p>
      <h1>Historique et progression</h1>
      <p className="lead">Édition : {saison.nom || `#${saison.id}`}. Les éléments ci-dessous proviennent uniquement des données publiées ou validées.</p>
      {err && <p className="erreur">{err}</p>}

      <div className="historique-grille">
        <article className="carte">
          <h2>Progression et qualification</h2>
          {!progression && <p className="empty">Chargement…</p>}
          {progression?.statut === "reglement_absent" && (
            <p className="notice">Aucun règlement actif n’est rattaché à cette édition : la qualification reste indéterminée.</p>
          )}
          {progression?.lignes?.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Club</th><th>Groupe</th><th>Pts</th><th>Joués</th><th>Restants</th><th>Statut</th></tr></thead>
                <tbody>
                  {progression.lignes.map((row) => (
                    <tr key={row.club_id}>
                      <td>{row.club_nom}</td>
                      <td>{row.groupe || "—"}</td>
                      <td>{row.points}</td>
                      <td>{row.matchs_joues}</td>
                      <td>{row.matchs_restants}</td>
                      <td title={row.explication}>{statutTexte(row.statut_qualification)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>

        <article className="carte">
          <h2>Records de l’édition</h2>
          {records.length === 0 && <p className="empty">Aucun record calculable à partir des matchs validés.</p>}
          <ul className="liste-simple">
            {records.map((record) => <li key={`${record.code}-${record.match_id || record.joueur_id || "edition"}`}><strong>{record.message}</strong><span>{record.source}</span></li>)}
          </ul>
        </article>
      </div>

      <article className="carte">
        <h2>Timeline officielle</h2>
        {timeline.length === 0 && <p className="empty">Aucun événement officiel publié.</p>}
        <ol className="timeline-liste">
          {timeline.map((item, index) => (
            <li key={`${item.source}-${item.match_id || item.document_id || item.actualite_id || item.decision_id || index}`}>
              <time>{dateTexte(item.date)}</time>
              <strong>{item.titre}</strong>
              <span>{item.type}</span>
            </li>
          ))}
        </ol>
      </article>

      <article className="carte">
        <h2>Historique public des actions</h2>
        {historique.length === 0 && <p className="empty">Aucune action publique enregistrée pour cette édition.</p>}
        <ul className="liste-simple">
          {historique.map((row) => <li key={row.id}><strong>{row.action} · {row.table_name} #{row.record_id}</strong><span>{dateTexte(row.created_at)}</span></li>)}
        </ul>
      </article>
    </section>
  );
}
