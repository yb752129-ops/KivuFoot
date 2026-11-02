import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { LiveMinute } from "../components/Chrono.jsx";
import { startVisibleRefresh } from "../liveRefresh.js";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import { IcoCalendrier, IcoEpingle } from "../icons.jsx";
import {
  displayValue,
  findPublicClub,
  formatPublicDate,
  formatPublicDay,
  formatPublicKickoff,
  formatPublicRound,
  formatPublicScore,
  numericValue,
  scorePublicVisible,
  PublicClubLogo,
  publicClubName,
} from "../components/PublicDesign.jsx";
import { dernierFaitLive, formatMinute, groupMatchsByJournee, labelEvenement, journeeTitre } from "../display.js";
import { ETAPES_PHASE_FINALE, libelleCartePhaseFinale, numeroterMatchsPhase } from "../phaseFinale.js";

const FILTRES = [
  ["tous", "Tous"],
  ["avenir", "À venir"],
  ["termines", "Terminés"],
  ["direct", "En cours"],
  ["phase-finale", "Phase finale"],
];
const STATUTS_PUBLICS = new Set(["programme", "en_cours", "termine", "valide"]);

function filtreDepuisURL(searchParams) {
  const value = searchParams.get("filtre");
  return FILTRES.some(([id]) => id === value) ? value : "tous";
}

function tourDepuisURL(searchParams) {
  const value = searchParams.get("tour");
  return ETAPES_PHASE_FINALE.some((phase) => phase.id === value) ? value : "barrage";
}

function statutLabel(statut) {
  if (statut === "programme") return "À VENIR";
  if (statut === "en_cours") return "En cours";
  if (statut === "termine" || statut === "valide") return "Résultat";
  return "À VENIR";
}

function classeHalo(match) {
  if (match.statut === "programme") return "halo-accent";
  if (match.statut === "en_cours") return "halo-live";
  return match.id % 2 === 0 ? "halo-blue" : "halo-gold";
}

function comparerDateProgramme(a, b) {
  if (!a.date_heure && !b.date_heure) return Number(a.id || 0) - Number(b.id || 0);
  if (!a.date_heure) return 1;
  if (!b.date_heure) return -1;
  return new Date(a.date_heure) - new Date(b.date_heure);
}

function scoreWinners(match) {
  if (!scorePublicVisible(match)) return { home: false, away: false };
  const home = numericValue(match.score_domicile);
  const away = numericValue(match.score_exterieur);
  if (home === null || away === null || home === away) return { home: false, away: false };
  return { home: home > away, away: away > home };
}

function classeEvenementLive(event) {
  if (event?.type === "carton_jaune") return "is-yellow";
  if (event?.type === "carton_rouge") return "is-red";
  if (event?.type === "remplacement") return "is-substitution";
  if (event?.type === "but" || event?.type === "but_contre_son_camp" || event?.type === "penalty") return "is-goal";
  return "";
}

function PublicMatchCard({ match, clubsById, saisonClubs, event, numerotationPhase }) {
  const home = findPublicClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const away = findPublicClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const homeName = publicClubName(clubsById, saisonClubs, match.equipe_domicile_id);
  const awayName = publicClubName(clubsById, saisonClubs, match.equipe_exterieur_id);
  const winners = scoreWinners(match);
  const upcoming = !scorePublicVisible(match);
  const official = match.statut === "valide";
  const numeroPhase = numerotationPhase?.get(Number(match.id));
  const libellePhase = libelleCartePhaseFinale(match.phase, numeroPhase);
  return (
    <Link to={`/matchs/${match.id}`} className={`kf-public-match-card ${classeHalo(match)}`}>
      <div className="kf-public-match-top">
        {match.statut === "en_cours" && !match.ended_at ? (
          <span
            className={`kf-public-match-status kf-public-live-indicator${match.periode === "mi_temps" ? " is-break" : ""}`}
            aria-label={match.periode === "mi_temps" ? "Mi-temps" : "En cours"}
          >
            <i aria-hidden="true" />
            {match.periode === "mi_temps" && <b>MT</b>}
          </span>
        ) : (
          <span className="kf-public-match-status">{statutLabel(match.statut)}</span>
        )}
        {libellePhase ? (
          <span className="kf-public-match-phase-meta">
            <strong className="kf-public-match-phase-tag">{libellePhase}</strong>
            {!upcoming && match.date_heure && <span className="kf-public-match-date">{formatPublicDate(match.date_heure)}</span>}
          </span>
        ) : (
          <span>{upcoming ? formatPublicRound(match.journee) : formatPublicDate(match.date_heure)}</span>
        )}
      </div>
      <div className="kf-public-match-teams">
        <span className={`kf-public-match-team${winners.home ? " winner" : ""}`}>
          <PublicClubLogo club={home} name={homeName} />
          <strong>{homeName}</strong>
        </span>
        <span className="kf-public-match-score-wrap">
          <strong className="kf-public-match-score">{formatPublicScore(match)}</strong>
          {match.statut === "en_cours" && !match.ended_at && <LiveMinute match={match} className="kf-public-live-minute" />}
        </span>
        <span className={`kf-public-match-team away${winners.away ? " winner" : ""}`}>
          <PublicClubLogo club={away} name={awayName} />
          <strong>{awayName}</strong>
        </span>
      </div>
      {upcoming && <p className="kf-public-match-kickoff">{match.date_heure ? formatPublicKickoff(match.date_heure) : "Date et heure à confirmer"}</p>}
      {event && (
        <p className={`kf-public-live-event ${classeEvenementLive(event)}`}>
          {formatMinute(event.minute, event.minute_additionnelle)} · {labelEvenement(event)}
        </p>
      )}
      <div className="kf-public-match-bottom">
        <span><IcoEpingle /> {match.stade || "—"}</span>
        {!upcoming && !libellePhase && <span><IcoCalendrier /> {formatPublicRound(match.journee)}</span>}
      </div>
      {official && <span className="kf-public-official-note">Résultat officiel</span>}
    </Link>
  );
}

function GroupeMatchs({ groupe, clubsById, saisonClubs, evtsById, numerotationPhase }) {
  const stadium = groupe.items.find((match) => match.stade)?.stade || "—";
  return (
    <section className="kf-public-match-group">
      <div className="kf-public-group-label">
        <strong>{groupe.code === "—" ? "—" : `${journeeTitre(groupe.code)} · ${formatPublicDay(groupe.date)}`}</strong>
        <span>{stadium}</span>
      </div>
      <div className="kf-public-result-group">
        {groupe.items.map((match) => (
          <PublicMatchCard
            key={match.id}
            match={match}
            clubsById={clubsById}
            saisonClubs={saisonClubs}
            event={evtsById[match.id] || null}
            numerotationPhase={numerotationPhase}
          />
        ))}
      </div>
    </section>
  );
}

export default function Matchs() {
  const { saison, clubsById, saisonClubs } = useKivu();
  const [searchParams, setSearchParams] = useSearchParams();
  const [matchs, setMatchs] = useState([]);
  const [evtsById, setEvtsById] = useState({});
  const [err, setErr] = useState("");
  const filtre = filtreDepuisURL(searchParams);
  const phaseTour = tourDepuisURL(searchParams);

  useEffect(() => {
    if (!saison) {
      setMatchs([]);
      setEvtsById({});
      return undefined;
    }
    let stop = false;
    setErr("");

    async function charge() {
      try {
        const rows = await api.matchs(saison.id);
        if (stop) return;
        const list = Array.isArray(rows) ? rows : [];
        setMatchs(list);
        const lives = list.filter((match) => match.statut === "en_cours" && !match.ended_at);
        if (!lives.length) {
          setEvtsById({});
          return;
        }
        const pairs = await Promise.all(
          lives.map((match) => api.evenementsPublics(match.id)
            .then((events) => [match.id, dernierFaitLive(events)])
            .catch(() => [match.id, null])),
        );
        if (!stop) setEvtsById(Object.fromEntries(pairs));
      } catch (error) {
        if (!stop) {
          setMatchs([]);
          setErr(error.message || "Impossible de charger les matchs.");
        }
      }
    }

    const stopRefresh = startVisibleRefresh(charge, 10000);
    return () => {
      stop = true;
      stopRefresh();
    };
  }, [saison]);

  const changerFiltre = (valeur) => {
    setSearchParams((courants) => {
      const suivants = new URLSearchParams(courants);
      if (valeur === "tous") suivants.delete("filtre");
      else suivants.set("filtre", valeur);
      if (valeur !== "phase-finale") suivants.delete("tour");
      else if (!ETAPES_PHASE_FINALE.some((phase) => phase.id === suivants.get("tour"))) suivants.set("tour", "barrage");
      return suivants;
    });
  };

  const changerTour = (valeur) => {
    setSearchParams((courants) => {
      const suivants = new URLSearchParams(courants);
      suivants.set("filtre", "phase-finale");
      suivants.set("tour", valeur);
      return suivants;
    });
  };

  const affiches = useMemo(() => {
    if (filtre === "avenir") return matchs.filter((match) => match.statut === "programme");
    if (filtre === "termines") return matchs.filter((match) => ["termine", "valide"].includes(match.statut));
    if (filtre === "direct") return matchs.filter((match) => match.statut === "en_cours" && !match.ended_at);
    if (filtre === "phase-finale") return [];
    return matchs.filter((match) => STATUTS_PUBLICS.has(match.statut));
  }, [filtre, matchs]);

  const numeroPhaseParMatch = useMemo(() => numeroterMatchsPhase(matchs), [matchs]);
  const matchsDuTour = useMemo(
    () => matchs
      .filter((match) => match.phase === phaseTour && STATUTS_PUBLICS.has(match.statut))
      .sort(comparerDateProgramme),
    [matchs, phaseTour],
  );

  const aVenir = [...affiches]
    .filter((match) => match.statut === "programme")
    .sort(comparerDateProgramme);
  const lives = [...affiches]
    .filter((match) => match.statut === "en_cours" && !match.ended_at)
    .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const termines = [...affiches]
    .filter((match) => ["termine", "valide"].includes(match.statut))
    .sort((a, b) => new Date(b.date_heure) - new Date(a.date_heure));
  const groupesTermines = groupMatchsByJournee(termines);
  const groupesAvenir = groupMatchsByJournee(aVenir);
  const phaseActive = ETAPES_PHASE_FINALE.find((phase) => phase.id === phaseTour) || ETAPES_PHASE_FINALE[0];

  return (
    <section className="kf-public-page kf-public-matches">
      <h1 className="screen-title">Matchs</h1>
      <p className="screen-subtitle">{saison?.nom || "—"} · {matchs.length} résultats</p>

      <div className="kf-public-tabs kf-public-match-tabs" role="tablist" aria-label="Filtrer les matchs">
        {FILTRES.map(([value, label]) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={filtre === value}
            className={filtre === value ? "active" : ""}
            onClick={() => changerFiltre(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {err && <p className="kf-public-error">{err}</p>}

      {filtre === "phase-finale" ? (
        <>
          <div className="kf-public-tabs kf-public-phase-round-tabs" role="tablist" aria-label="Choisir un tour de phase finale">
            {ETAPES_PHASE_FINALE.map((phase) => (
              <button
                key={phase.id}
                type="button"
                role="tab"
                aria-selected={phaseTour === phase.id}
                className={phaseTour === phase.id ? "active" : ""}
                onClick={() => changerTour(phase.id)}
              >
                {phase.filtre}
              </button>
            ))}
          </div>

          <section className="kf-public-match-section" aria-label={`Phase finale : ${phaseActive.titre}`}>
            <div className="kf-public-group-label">
              <strong>{phaseActive.titre}</strong>
              <span>{matchsDuTour.length} match{matchsDuTour.length > 1 ? "s" : ""}</span>
            </div>
            {matchsDuTour.length === 0 ? (
              <div className="kf-public-empty"><strong>Programme à communiquer</strong></div>
            ) : (
              <div className="kf-public-result-group" id="kf-phase-finale-matchs">
                {matchsDuTour.map((match) => (
                  <PublicMatchCard
                    key={match.id}
                    match={match}
                    clubsById={clubsById}
                    saisonClubs={saisonClubs}
                    event={evtsById[match.id] || null}
                    numerotationPhase={numeroPhaseParMatch}
                  />
                ))}
              </div>
            )}
          </section>
        </>
      ) : (
        <>
          {lives.length > 0 && (
            <section className="kf-public-match-section">
              <div className="kf-public-group-label"><strong>En cours</strong><span>{lives.length} match{lives.length > 1 ? "s" : ""}</span></div>
              <div className="kf-public-result-group">
                {lives.map((match) => (
                  <PublicMatchCard
                    key={match.id}
                    match={match}
                    clubsById={clubsById}
                    saisonClubs={saisonClubs}
                    event={evtsById[match.id] || null}
                    numerotationPhase={numeroPhaseParMatch}
                  />
                ))}
              </div>
            </section>
          )}

          {filtre !== "termines" && filtre !== "direct" && (
            <section className="kf-public-match-section">
              <div className="kf-public-group-label"><strong>À venir</strong><span>{aVenir.length} match{aVenir.length > 1 ? "s" : ""}</span></div>
              {groupesAvenir.length === 0 ? (
                <div className="kf-public-empty"><strong>Aucun match programmé</strong></div>
              ) : (
                groupesAvenir.map((groupe) => (
                  <GroupeMatchs
                    key={groupe.code}
                    groupe={groupe}
                    clubsById={clubsById}
                    saisonClubs={saisonClubs}
                    evtsById={evtsById}
                    numerotationPhase={numeroPhaseParMatch}
                  />
                ))
              )}
            </section>
          )}

          {filtre !== "avenir" && filtre !== "direct" && (
            <section className="kf-public-match-section">
              <div className="kf-public-group-label"><strong>Terminés</strong><span>{termines.length} résultats</span></div>
              {groupesTermines.length === 0 ? (
                <div className="kf-public-empty"><strong>Pas encore de résultat public</strong></div>
              ) : (
                <>
                  <p className="kf-public-official-summary">Résultats officiels</p>
                  {groupesTermines.map((groupe) => (
                    <GroupeMatchs
                      key={groupe.code}
                      groupe={groupe}
                      clubsById={clubsById}
                      saisonClubs={saisonClubs}
                      evtsById={evtsById}
                      numerotationPhase={numeroPhaseParMatch}
                    />
                  ))}
                </>
              )}
            </section>
          )}

          {affiches.length === 0 && !err && filtre !== "direct" && (
            <div className="kf-public-empty"><strong>Aucun match à afficher</strong></div>
          )}
        </>
      )}
    </section>
  );
}
