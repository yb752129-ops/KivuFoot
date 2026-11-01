import { useEffect, useMemo, useState } from "react";
import "./phaseFinale.css";
import { api } from "../api.js";
import { useKivu, clubName } from "../context.jsx";
import { stripDemo } from "../display.js";
import Scoreboard from "../components/Scoreboard.jsx";
import { ETAPES_PHASE_FINALE, vainqueurMatchEliminatoire } from "../phaseFinale.js";

function nomClub(clubsById, id) {
  return stripDemo(clubName(clubsById, id)) || "Équipe à confirmer";
}

function formatDateMatch(value) {
  if (!value) return "Date à fixer";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date à fixer";
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function MatchEliminatoire({ match, clubsById, saisonClubs }) {
  const decision = vainqueurMatchEliminatoire(match);
  const nomVainqueur = decision ? nomClub(clubsById, decision.equipeId) : "";
  const resultatValide = match.statut === "valide";

  return (
    <article className="phase-finale-match">
      <div className="phase-finale-match-meta">
        <span>Match {match.id}</span>
        <time dateTime={match.date_heure || undefined}>{formatDateMatch(match.date_heure)}</time>
      </div>
      <Scoreboard
        match={match}
        clubsById={clubsById}
        saisonClubs={saisonClubs}
        to={`/matchs/${match.id}`}
      />
      {resultatValide && decision ? (
        <p className="phase-finale-qualifie"><span aria-hidden="true">✓</span> Qualifié · {nomVainqueur}</p>
      ) : resultatValide ? (
        <p className="phase-finale-attente">Qualification à confirmer</p>
      ) : match.statut === "termine" ? (
        <p className="phase-finale-attente">Résultat en attente de validation</p>
      ) : (
        <p className="phase-finale-attente">Match programmé ou en cours</p>
      )}
    </article>
  );
}

export default function PhaseFinale() {
  const { saison, clubsById, saisonClubs } = useKivu();
  const [matchs, setMatchs] = useState([]);
  const [loading, setLoading] = useState(Boolean(saison?.id));
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    let actif = true;
    if (!saison?.id) {
      setMatchs([]);
      setLoading(false);
      setErreur("");
      return () => { actif = false; };
    }

    setLoading(true);
    setErreur("");
    api.matchs(saison.id)
      .then((rows) => {
        if (!actif) return;
        setMatchs((rows || []).filter((match) => ETAPES_PHASE_FINALE.some((phase) => phase.id === match.phase)));
      })
      .catch((error) => {
        if (!actif) return;
        setMatchs([]);
        setErreur(error.message || "Impossible de charger les matchs de phase finale.");
      })
      .finally(() => { if (actif) setLoading(false); });

    return () => { actif = false; };
  }, [saison?.id]);

  const parPhase = useMemo(() => {
    const groupes = Object.fromEntries(ETAPES_PHASE_FINALE.map((phase) => [phase.id, []]));
    for (const match of matchs) {
      if (groupes[match.phase]) groupes[match.phase].push(match);
    }
    for (const rencontres of Object.values(groupes)) {
      rencontres.sort((a, b) => {
        const dateA = Date.parse(a.date_heure || "");
        const dateB = Date.parse(b.date_heure || "");
        const comparaisonDate = (Number.isFinite(dateA) ? dateA : 0) - (Number.isFinite(dateB) ? dateB : 0);
        return comparaisonDate || Number(a.id || 0) - Number(b.id || 0);
      });
    }
    return groupes;
  }, [matchs]);

  const saisonTitre = saison?.nom || saison?.libelle || (saison?.annee ? `Saison ${saison.annee}` : "Saison active");

  return (
    <section className="hero phase-finale-page">
      <header className="phase-finale-header">
        <p className="kicker">Compétition · {saisonTitre}</p>
        <h1>Phase finale</h1>
        <p className="lead">Des barrages à la finale, à partir des matchs enregistrés dans cette saison.</p>
      </header>

      <p className="phase-finale-note">
        Seuls les résultats validés déterminent un qualifié ou une élimination. Les appariements affichés viennent des matchs enregistrés : aucun n’est créé automatiquement.
      </p>

      {erreur && <p className="erreur" role="alert">{erreur}</p>}
      {!saison?.id && <p className="empty">Aucune saison active pour afficher la phase finale.</p>}
      {loading && <p className="empty" aria-live="polite">Chargement de la phase finale…</p>}
      {!loading && !erreur && saison?.id && matchs.length === 0 && (
        <p className="empty">Aucun match de phase finale enregistré pour cette saison.</p>
      )}

      {saison?.id && !loading && !erreur && matchs.length > 0 && (
        <div className="phase-finale-board" role="region" aria-label="Tableau des barrages à la finale" tabIndex={0}>
          {ETAPES_PHASE_FINALE.map((phase, index) => {
            const rencontres = parPhase[phase.id] || [];
            return (
              <section className="phase-finale-round" key={phase.id} aria-labelledby={`phase-finale-${phase.id}`}>
                <div className="phase-finale-round-heading">
                  <span className="phase-finale-round-index">0{index + 1}</span>
                  <h2 id={`phase-finale-${phase.id}`}>{phase.titre}</h2>
                  {index < ETAPES_PHASE_FINALE.length - 1 && <span className="phase-finale-arrow" aria-hidden="true">→</span>}
                </div>
                {rencontres.length === 0 ? (
                  <p className="phase-finale-round-empty">Aucun match enregistré.</p>
                ) : (
                  <div className="phase-finale-matches">
                    {rencontres.map((match) => (
                      <MatchEliminatoire
                        key={match.id}
                        match={match}
                        clubsById={clubsById}
                        saisonClubs={saisonClubs}
                      />
                    ))}
                  </div>
                )}
              </section>
            );
          })}
        </div>
      )}
    </section>
  );
}
