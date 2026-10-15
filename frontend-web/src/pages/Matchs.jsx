import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
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

const FILTRES = [
  ["tous", "Tous"],
  ["avenir", "À venir"],
  ["termines", "Terminés"],
  ["direct", "En direct"],
];

function statutLabel(statut) {
  if (statut === "programme") return "À VENIR";
  if (statut === "en_cours") return "En direct";
  if (statut === "termine" || statut === "valide") return "Résultat";
  return "À VENIR";
}

function classeHalo(match) {
  if (match.statut === "programme") return "halo-accent";
  if (match.statut === "en_cours") return "halo-live";
  return match.id % 2 === 0 ? "halo-blue" : "halo-gold";
}

function scoreWinners(match) {
  if (!scorePublicVisible(match)) return { home: false, away: false };
  const home = numericValue(match.score_domicile);
  const away = numericValue(match.score_exterieur);
  if (home === null || away === null || home === away) return { home: false, away: false };
  return { home: home > away, away: away > home };
}

function PublicMatchCard({ match, clubsById, saisonClubs, event }) {
  const home = findPublicClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const away = findPublicClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const homeName = publicClubName(clubsById, saisonClubs, match.equipe_domicile_id);
  const awayName = publicClubName(clubsById, saisonClubs, match.equipe_exterieur_id);
  const winners = scoreWinners(match);
  const upcoming = !scorePublicVisible(match);
  const official = match.statut === "valide";
  return (
    <Link to={`/matchs/${match.id}`} className={`kf-public-match-card ${classeHalo(match)}`}>
      <div className="kf-public-match-top">
        <span className="kf-public-match-status">{statutLabel(match.statut)}</span>
        <span>{upcoming ? formatPublicRound(match.journee) : formatPublicDate(match.date_heure)}</span>
      </div>
      <div className="kf-public-match-teams">
        <span className={`kf-public-match-team${winners.home ? " winner" : ""}`}>
          <PublicClubLogo club={home} name={homeName} />
          <strong>{homeName}</strong>
        </span>
        <strong className="kf-public-match-score">{formatPublicScore(match)}</strong>
        <span className={`kf-public-match-team away${winners.away ? " winner" : ""}`}>
          <PublicClubLogo club={away} name={awayName} />
          <strong>{awayName}</strong>
        </span>
      </div>
      {upcoming && <p className="kf-public-match-kickoff">{formatPublicKickoff(match.date_heure)}</p>}
      {event && (
        <p className="kf-public-live-event">
          {formatMinute(event.minute, event.minute_additionnelle)} · {labelEvenement(event)}
        </p>
      )}
      <div className="kf-public-match-bottom">
        <span><IcoEpingle /> {match.stade || "—"}</span>
        {!upcoming && <span><IcoCalendrier /> {formatPublicRound(match.journee)}</span>}
      </div>
      {official && <span className="kf-public-official-note">Résultat officiel</span>}
    </Link>
  );
}

function GroupeMatchs({ groupe, clubsById, saisonClubs, evtsById }) {
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
          />
        ))}
      </div>
    </section>
  );
}

export default function Matchs() {
  const { saison, clubsById, saisonClubs } = useKivu();
  const [matchs, setMatchs] = useState([]);
  const [filtre, setFiltre] = useState("tous");
  const [evtsById, setEvtsById] = useState({});
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!saison) {
      setMatchs([]);
      setEvtsById({});
      return undefined;
    }
    let stop = false;
    setErr("");
    api.matchs(saison.id)
      .then(async (rows) => {
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
      })
      .catch((error) => {
        if (!stop) {
          setMatchs([]);
          setErr(error.message || "Impossible de charger les matchs.");
        }
      });
    return () => { stop = true; };
  }, [saison]);

  const affiches = useMemo(() => {
    if (filtre === "avenir") return matchs.filter((match) => match.statut === "programme");
    if (filtre === "termines") return matchs.filter((match) => ["termine", "valide"].includes(match.statut));
    if (filtre === "direct") return matchs.filter((match) => match.statut === "en_cours" && !match.ended_at);
    return matchs.filter((match) => ["programme", "en_cours", "termine", "valide"].includes(match.statut));
  }, [filtre, matchs]);

  const aVenir = [...affiches]
    .filter((match) => match.statut === "programme")
    .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const lives = [...affiches]
    .filter((match) => match.statut === "en_cours" && !match.ended_at)
    .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const termines = [...affiches]
    .filter((match) => ["termine", "valide"].includes(match.statut))
    .sort((a, b) => new Date(b.date_heure) - new Date(a.date_heure));
  const groupesTermines = groupMatchsByJournee(termines);
  const groupesAvenir = groupMatchsByJournee(aVenir);

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
            onClick={() => setFiltre(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {err && <p className="kf-public-error">{err}</p>}

      {filtre === "direct" && lives.length === 0 && (
        <div className="kf-public-empty"><strong>Aucun match en direct</strong></div>
      )}
      {lives.length > 0 && (
        <section className="kf-public-match-section">
          <div className="kf-public-group-label"><strong>En direct</strong><span>{lives.length} match{lives.length > 1 ? "s" : ""}</span></div>
          <div className="kf-public-result-group">
            {lives.map((match) => (
              <PublicMatchCard
                key={match.id}
                match={match}
                clubsById={clubsById}
                saisonClubs={saisonClubs}
                event={evtsById[match.id] || null}
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
              <GroupeMatchs key={groupe.code} groupe={groupe} clubsById={clubsById} saisonClubs={saisonClubs} evtsById={evtsById} />
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
                <GroupeMatchs key={groupe.code} groupe={groupe} clubsById={clubsById} saisonClubs={saisonClubs} evtsById={evtsById} />
              ))}
            </>
          )}
        </section>
      )}

      {affiches.length === 0 && !err && filtre !== "direct" && (
        <div className="kf-public-empty"><strong>Aucun match à afficher</strong></div>
      )}
    </section>
  );
}
