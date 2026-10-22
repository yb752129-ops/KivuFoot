import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import {
  addCivilDays,
  civilDate,
  stripDemo,
  todayCivil,
} from "../display.js";
import {
  compareClassementRows,
  displayDifference,
  displayValue,
  findPublicClub,
  followedPublicClubId,
  formatPublicDate,
  formatPublicDay,
  formatPublicKickoff,
  formatPublicRound,
  PublicClubLogo,
  scorePublicVisible,
  StatutEquipeBadge,
} from "../components/PublicDesign.jsx";
import Chrono, { LiveMinute } from "../components/Chrono.jsx";
import { startVisibleRefresh } from "../liveRefresh.js";
import { IcoCalendrier, IcoEpingle } from "../icons.jsx";

const CATEGORIES = {
  annonce: "Annonce officielle",
  match_competition: "Match / compétition",
  retour_journee: "Retour de journée",
  homme_du_match: "Homme du match",
  performance: "Performance",
  photo_moment: "Photo / moment",
  fair_play: "Fair-play",
  information_importante: "Information importante",
};

function textClub(clubsById, saisonClubs, id) {
  const club = findPublicClub(clubsById, saisonClubs, id);
  return club?.nom ? stripDemo(club.nom) : "—";
}

function titreActualite(item) {
  const titre = String(item?.titre || "");
  const sansPictogrammes = titre
    .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\uFE0F]/gu, "")
    .replace(/\s{2,}/g, " ")
    .trim();
  return sansPictogrammes || "—";
}

function isFinished(match) {
  return ["termine", "valide"].includes(match?.statut);
}

function isLive(match) {
  return match?.statut === "en_cours" && !match?.ended_at;
}

function homeLiveStatus(match) {
  return match?.periode === "mi_temps" ? "MT" : "";
}

function HomeLiveMinute({ match, className = "kf-home-live-minute" }) {
  return <LiveMinute match={match} className={className} />;
}

function isScheduled(match) {
  return match?.statut === "programme";
}

function homeDayStatusOrder(match) {
  if (isLive(match)) return 0;
  if (isScheduled(match)) return 1;
  if (isFinished(match)) return 2;
  return 3;
}

function homeDayLabel(offset, iso) {
  if (offset === -1) return "Hier";
  if (offset === 0) return "Aujourd’hui";
  if (offset === 1) return "Demain";
  const date = new Date(`${iso}T12:00:00Z`);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "Africa/Lubumbashi",
  }).format(date).replace(/\./g, "");
}

function dejaInstallee() {
  if (typeof window === "undefined") return false;
  return window.matchMedia?.("(display-mode: standalone)").matches
    || window.navigator.standalone === true
    || document.referrer.startsWith("android-app://");
}

function HomeSkeleton() {
  return (
    <section className="kf-home-skeleton" aria-label="Chargement de l’accueil" aria-busy="true">
      <div className="kf-loading-title-block" aria-hidden="true">
        <span className="kf-skeleton kf-skeleton-kicker" />
        <span className="kf-skeleton kf-skeleton-title" />
        <span className="kf-skeleton kf-skeleton-subtitle" />
      </div>
      <div className="kf-home-skeleton-card" aria-hidden="true">
        <span className="kf-skeleton kf-skeleton-card-line kf-skeleton-card-line-short" />
        <span className="kf-skeleton kf-skeleton-card-score" />
        <span className="kf-skeleton kf-skeleton-card-line" />
      </div>
      <div className="kf-loading-ranking" aria-hidden="true">
        <div className="kf-loading-ranking-head">
          <span className="kf-skeleton kf-skeleton-section-title" />
          <span className="kf-skeleton kf-skeleton-section-meta" />
        </div>
        {Array.from({ length: 5 }, (_, index) => (
          <div className="kf-loading-ranking-row" key={index}>
            <span className="kf-skeleton kf-skeleton-row-rank" />
            <span className="kf-skeleton kf-skeleton-row-club" />
            <span className="kf-skeleton kf-skeleton-row-stat" />
            <span className="kf-skeleton kf-skeleton-row-stat" />
          </div>
        ))}
      </div>
    </section>
  );
}

function compactHomeTeamName(name) {
  return name === "NUTRITION + OPHTALMOLOGIE" ? "NUTRITION + OPHT." : name;
}

function HomeTeam({ club, name, align = "left", label = name }) {
  return (
    <span className={`kf-home-team kf-home-team-${align}${club?.statut && club.statut !== "actif" ? " team-status-muted" : ""}`}>
      <PublicClubLogo club={club} name={name} statut={club?.statut} />
      <span>{label}</span>
      <StatutEquipeBadge statut={club?.statut} compact />
    </span>
  );
}

function HomeMatchMeta({ match }) {
  const date = scorePublicVisible(match)
    ? formatPublicDate(match.date_heure)
    : formatPublicKickoff(match.date_heure);
  return (
    <div className="kf-home-match-meta">
      <span><IcoCalendrier /> {date}</span>
      <span><IcoEpingle /> {match.stade || "—"}</span>
      {scorePublicVisible(match) && <span>{formatPublicRound(match.journee)}</span>}
    </div>
  );
}

function HomeResultCard({ match, clubsById, saisonClubs }) {
  const home = findPublicClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const away = findPublicClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const homeName = textClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const awayName = textClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const homeScore = displayValue(match.score_domicile);
  const awayScore = displayValue(match.score_exterieur);
  const homeWinner = Number.isFinite(Number(match.score_domicile)) && Number.isFinite(Number(match.score_exterieur))
    && Number(match.score_domicile) > Number(match.score_exterieur);
  const awayWinner = Number.isFinite(Number(match.score_domicile)) && Number.isFinite(Number(match.score_exterieur))
    && Number(match.score_exterieur) > Number(match.score_domicile);

  return (
    <Link to={`/matchs/${match.id}`} className="kf-home-match-card kf-home-result-card">
      <div className="kf-home-card-top">
        <span className="kf-home-status">Résultat officiel</span>
        <span>{formatPublicRound(match.journee)}</span>
      </div>
      <div className="kf-home-card-teams">
        <HomeTeam club={home} name={homeName} label={compactHomeTeamName(homeName)} />
        <strong className="kf-home-card-score" aria-label={`Score ${homeScore} à ${awayScore}`}>
          <span className={homeWinner ? "winner" : ""}>{homeScore}</span>
          <i>–</i>
          <span className={awayWinner ? "winner" : ""}>{awayScore}</span>
        </strong>
        <HomeTeam club={away} name={awayName} label={compactHomeTeamName(awayName)} align="right" />
      </div>
      <HomeMatchMeta match={match} />
    </Link>
  );
}

function HomeUpcomingCard({ match, clubsById, saisonClubs }) {
  const home = findPublicClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const away = findPublicClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const homeName = textClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const awayName = textClub(clubsById, saisonClubs, match.equipe_exterieur_id);

  return (
    <Link to={`/matchs/${match.id}`} className="kf-home-match-card kf-home-upcoming-card">
      <div className="kf-home-card-top">
        <span className="kf-home-status">À VENIR</span>
        <span>{formatPublicRound(match.journee)}</span>
      </div>
      <div className="kf-home-upcoming-title" title={`${homeName} — ${awayName}`}>
        <HomeTeam club={home} name={homeName} label={compactHomeTeamName(homeName)} />
        <strong>—</strong>
        <HomeTeam club={away} name={awayName} label={compactHomeTeamName(awayName)} align="right" />
      </div>
      <HomeMatchMeta match={match} />
    </Link>
  );
}

function HomeLiveCard({ match, clubsById, saisonClubs }) {
  const home = findPublicClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const away = findPublicClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const homeName = textClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const awayName = textClub(clubsById, saisonClubs, match.equipe_exterieur_id);

  return (
    <Link to={`/matchs/${match.id}`} className="kf-home-live-card">
      <div className="kf-home-live-top">
        <span
          className={match.periode === "mi_temps" ? "is-break" : ""}
          aria-label={match.periode === "mi_temps" ? "Mi-temps" : "En cours"}
        >
          <i aria-hidden="true" />
          {match.periode === "mi_temps" && <span className="live-break-code">MT</span>}
        </span>
        <span>{formatPublicRound(match.journee)}</span>
      </div>
      <div className="kf-home-live-teams">
        <HomeTeam club={home} name={homeName} label={compactHomeTeamName(homeName)} />
        <span className="kf-home-live-score-wrap">
          <strong>{displayValue(match.score_domicile)}–{displayValue(match.score_exterieur)}</strong>
          <HomeLiveMinute match={match} />
        </span>
        <HomeTeam club={away} name={awayName} label={compactHomeTeamName(awayName)} align="right" />
      </div>
    </Link>
  );
}

function HomeLiveCompactRow({ match, clubsById, saisonClubs }) {
  const homeName = textClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const awayName = textClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const home = findPublicClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const away = findPublicClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const pause = match.periode === "mi_temps";
  return (
    <Link to={`/matchs/${match.id}`} className="kf-home-live-compact-row">
      <span
        className={`kf-home-live-compact-status${pause ? " is-break" : ""}`}
        aria-label={pause ? "Mi-temps" : "En cours"}
      >
        <i aria-hidden="true" />
        {pause && <span className="live-break-code">MT</span>}
      </span>
      <span className="kf-home-live-compact-teams">
        <span className={home?.statut && home.statut !== "actif" ? "team-status-muted" : ""}><PublicClubLogo club={home} name={homeName} statut={home?.statut} />{homeName}<StatutEquipeBadge statut={home?.statut} compact /></span>
        <span className={away?.statut && away.statut !== "actif" ? "team-status-muted" : ""}><PublicClubLogo club={away} name={awayName} statut={away?.statut} />{awayName}<StatutEquipeBadge statut={away?.statut} compact /></span>
      </span>
      <span className="kf-home-live-compact-score">
        {displayValue(match.score_domicile)}–{displayValue(match.score_exterieur)}
        <small><HomeLiveMinute match={match} /></small>
      </span>
    </Link>
  );
}

function HomeDayRow({ match, clubsById, saisonClubs }) {
  const homeName = textClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const awayName = textClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const home = findPublicClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const away = findPublicClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const score = scorePublicVisible(match)
    ? `${displayValue(match.score_domicile)}–${displayValue(match.score_exterieur)}`
    : "—";
  const live = isLive(match);
  const pause = live && match.periode === "mi_temps";
  const status = live ? homeLiveStatus(match) : "";
  const heure = live
    ? (pause
      ? <span className="kf-home-live-minute">MT</span>
      : <HomeLiveMinute match={match} />)
    : isFinished(match)
      ? <span className="kf-home-live-minute">FT</span>
      : match.date_heure
        ? new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: "Africa/Bujumbura" }).format(new Date(match.date_heure))
        : "—";

  return (
    <Link to={`/matchs/${match.id}`} className="kf-home-day-row">
      <span className={`kf-home-day-time${live ? " live" : ""}`}>{heure}</span>
      <span className="kf-home-day-teams">
        <span className={home?.statut && home.statut !== "actif" ? "team-status-muted" : ""}><PublicClubLogo club={home} name={homeName} statut={home?.statut} /><span className="kf-home-day-name">{compactHomeTeamName(homeName)}</span><StatutEquipeBadge statut={home?.statut} compact /></span>
        <span className={away?.statut && away.statut !== "actif" ? "team-status-muted" : ""}><PublicClubLogo club={away} name={awayName} statut={away?.statut} /><span className="kf-home-day-name">{compactHomeTeamName(awayName)}</span><StatutEquipeBadge statut={away?.statut} compact /></span>
      </span>
      <span className={`kf-home-day-score${live ? " live" : ""}`}>
        {status && <small>{status}</small>}
        {score}
      </span>
    </Link>
  );
}

function HomeRanking({ classement, clubsById, saisonClubs, saison }) {
  const rows = [...classement].sort(compareClassementRows).slice(0, 5);
  const followedClubId = followedPublicClubId();

  return (
    <section className="kf-home-section kf-home-ranking" aria-labelledby="home-ranking-title">
      <div className="kf-home-section-head kf-home-ranking-head">
        <div>
          <h2 id="home-ranking-title">Mini-classement</h2>
          <p>{saison?.nom || "—"}</p>
        </div>
        <Link to="/classement">Classement complet <span aria-hidden="true">→</span></Link>
      </div>
      {rows.length === 0 ? (
        <p className="kf-home-empty">Aucun classement disponible pour le moment.</p>
      ) : (
        <div className="kf-home-rank-table" role="table" aria-label="Mini-classement de l’édition active">
          <div className="kf-home-rank-head" role="row">
            <span role="columnheader">#</span>
            <span role="columnheader">CLUB</span>
            <span role="columnheader">PTS</span>
            <span role="columnheader">J</span>
            <span role="columnheader">DIFF</span>
          </div>
          {rows.map((row, index) => {
            const club = findPublicClub(clubsById, saisonClubs, row.club_id);
            const name = stripDemo(row.club_nom || club?.nom || "—") || "—";
            const followed = followedClubId !== null && Number(row.club_id) === followedClubId;
            const statut = row.statut || club?.statut || "actif";
            return (
              <Link
                key={row.club_id ?? `${name}-${index}`}
                to={row.club_id ? `/clubs/${row.club_id}?saison_id=${saison?.id}` : "/clubs"}
                className={`kf-home-rank-row${followed ? " followed" : ""}${statut !== "actif" ? " team-status-muted" : ""}`}
                role="row"
              >
                <strong role="cell">{index + 1}</strong>
                <span className="kf-home-rank-club" role="cell"><PublicClubLogo club={club} name={name} statut={statut} /><span>{name}</span><StatutEquipeBadge statut={statut} compact /></span>
                <strong role="cell">{displayValue(row.points)}</strong>
                <span role="cell">{displayValue(row.matchs_joues)}</span>
                <span role="cell">{displayDifference(row.difference_buts)}</span>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}

function HomeNews({ actualites }) {
  return (
    <section className="kf-home-section kf-home-news" aria-labelledby="home-news-title">
      <div className="kf-home-section-head">
        <h2 id="home-news-title">Actualités</h2>
        <Link to="/actualites">Tout voir <span aria-hidden="true">→</span></Link>
      </div>
      {actualites.length === 0 ? (
        <p className="kf-home-empty">Aucune actualité pour le moment.</p>
      ) : (
        <div className="kf-home-news-grid">
          {actualites.slice(0, 2).map((item) => (
            <Link key={item.id} to={`/actualites/${item.id}`} className="kf-home-news-card">
              {item.image_principale_url ? <img src={item.image_principale_url} alt="" /> : <span className="kf-home-news-image" aria-hidden="true" />}
              <span className="kf-home-news-body">
                <small>{CATEGORIES[item.categorie] || "Publication"}</small>
                <strong>{titreActualite(item)}</strong>
                <span>{formatPublicDate(item.date_publication)}</span>
              </span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}

function HomeInstall({ installationEvent }) {
  const [message, setMessage] = useState("");

  async function installer() {
    if (!installationEvent) return;
    try {
      await installationEvent.prompt();
      const choice = await installationEvent.userChoice;
      setMessage(choice?.outcome === "accepted" ? "Installation lancée." : "Installation annulée.");
    } catch {
      setMessage("Installation indisponible pour le moment.");
    }
  }

  return (
    <section className="kf-home-install" aria-labelledby="home-install-title">
      <div>
        <p className="kf-home-install-kicker">Accès rapide</p>
        <h2 id="home-install-title">Installer l’application</h2>
        <p>Retrouvez KivuFoot depuis votre écran d’accueil.</p>
      </div>
      <button type="button" className="btn btn-primary" onClick={installer}>Installer</button>
      {message && <p className="kf-home-install-message" role="status">{message}</p>}
    </section>
  );
}

export default function Home() {
  const { saison, saisonClubs, clubsById, competition } = useKivu();
  const [classement, setClassement] = useState([]);
  const [matchs, setMatchs] = useState([]);
  const [actualites, setActualites] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [jourOffset, setJourOffset] = useState(0);
  const [installationEvent, setInstallationEvent] = useState(null);
  const [installee, setInstallee] = useState(dejaInstallee);

  useEffect(() => {
    function onBeforeInstallPrompt(event) {
      event.preventDefault();
      setInstallationEvent(event);
    }
    function onInstalled() {
      setInstallationEvent(null);
      setInstallee(true);
    }
    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  useEffect(() => {
    if (!saison) {
      setClassement([]);
      setMatchs([]);
      setActualites([]);
      setChargement(false);
      return undefined;
    }
    let stop = false;
    setChargement(true);

    async function charge() {
      const [classementResult, matchsResult, actualitesResult] = await Promise.all([
        api.classement(saison.id).catch(() => []),
        api.matchs(saison.id).catch(() => []),
        api.actualites({ competitionId: competition?.id || "", saisonId: saison.id, limit: 50 }).catch(() => []),
      ]);
      if (stop) return;
      const matches = Array.isArray(matchsResult) ? matchsResult : [];
      setClassement(Array.isArray(classementResult) ? classementResult : []);
      setMatchs(matches);
      setActualites(Array.isArray(actualitesResult) ? actualitesResult : []);
      setChargement(false);
    }

    const stopRefresh = startVisibleRefresh(charge, 10000);
    return () => {
      stop = true;
      stopRefresh();
    };
  }, [competition?.id, saison]);

  if (chargement) return <HomeSkeleton />;

  const lives = matchs.filter(isLive).sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const livePrincipal = lives[0] || null;
  const autresLives = lives.slice(1);
  const resultats = matchs.filter(isFinished).sort((a, b) => new Date(b.date_heure) - new Date(a.date_heure));
  const programmes = matchs.filter(isScheduled).sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const aujourdHui = todayCivil();
  const jour = addCivilDays(aujourdHui, jourOffset);
  const prochains = programmes.filter((match) => civilDate(match.date_heure) > jour);
  const matchsDuJour = matchs
    .filter((match) => civilDate(match.date_heure) === jour && !isLive(match))
    .sort((a, b) => (
      homeDayStatusOrder(a) - homeDayStatusOrder(b)
      || new Date(a.date_heure) - new Date(b.date_heure)
      || Number(a.id || 0) - Number(b.id || 0)
    ));
  const installable = Boolean(installationEvent) && !installee;

  return (
    <section className="kf-home-page" aria-label="Accueil">
      {lives.length > 0 && (
        <section className="kf-home-live-section" aria-labelledby="home-live-title">
          <div className="kf-home-section-head">
            <h2 id="home-live-title">En cours</h2>
          </div>
          <div className="kf-home-live-list">
            {livePrincipal && <HomeLiveCard match={livePrincipal} clubsById={clubsById} saisonClubs={saisonClubs} />}
            {autresLives.length > 0 && (
              <div className="kf-home-live-others" aria-label="Autres matchs en cours">
                <p className="kf-home-live-others-title">Autres matchs en cours</p>
                {autresLives.map((match) => (
                  <HomeLiveCompactRow key={match.id} match={match} clubsById={clubsById} saisonClubs={saisonClubs} />
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      {resultats[0] && (
        <section className="kf-home-section" aria-labelledby="home-result-title">
          <div className="kf-home-section-head">
            <h2 id="home-result-title">Dernier résultat</h2>
            <Link to="/matchs">Tous les matchs <span aria-hidden="true">→</span></Link>
          </div>
          <HomeResultCard match={resultats[0]} clubsById={clubsById} saisonClubs={saisonClubs} />
        </section>
      )}

      {prochains.length > 0 && (
        <section className="kf-home-section" aria-labelledby="home-next-title">
          <div className="kf-home-section-head">
            <div>
              <h2 id="home-next-title">Prochains matchs</h2>
              <p>Les prochaines affiches de l’édition active</p>
            </div>
            <Link to="/matchs">Tout voir <span aria-hidden="true">→</span></Link>
          </div>
          <div className="kf-home-upcoming-list">
            {prochains.slice(0, 3).map((match) => (
              <HomeUpcomingCard key={match.id} match={match} clubsById={clubsById} saisonClubs={saisonClubs} />
            ))}
          </div>
        </section>
      )}

      <section className="kf-home-section kf-home-day-schedule" aria-labelledby="home-day-title">
        <div className="kf-home-section-head">
          <div>
            <h2 id="home-day-title">Matchs du jour</h2>
            <p>{homeDayLabel(jourOffset, jour)}</p>
          </div>
          <div className="kf-home-day-nav" aria-label="Navigation des matchs par jour">
            <button type="button" aria-label="Afficher le jour précédent" onClick={() => setJourOffset((value) => value - 1)}>‹</button>
            <button type="button" aria-label="Afficher le jour suivant" onClick={() => setJourOffset((value) => value + 1)}>›</button>
          </div>
        </div>
        {matchsDuJour.length === 0
          ? <p className="kf-home-empty">Pas de match prévu ce jour.</p>
          : matchsDuJour.map((match) => <HomeDayRow key={match.id} match={match} clubsById={clubsById} saisonClubs={saisonClubs} />)}
      </section>

      <HomeRanking classement={classement} clubsById={clubsById} saisonClubs={saisonClubs} saison={saison} />
      <HomeNews actualites={actualites} />
      {installable && <HomeInstall installationEvent={installationEvent} />}
    </section>
  );
}
