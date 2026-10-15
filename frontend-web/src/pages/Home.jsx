import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import {
  addCivilDays,
  civilDate,
  dernierFaitLive,
  formatMinute,
  labelEvenement,
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
} from "../components/PublicDesign.jsx";
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

function isScheduled(match) {
  return match?.statut === "programme";
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

function HomeTeam({ club, name, align = "left" }) {
  return (
    <span className={`kf-home-team kf-home-team-${align}`}>
      <PublicClubLogo club={club} name={name} />
      <span>{name}</span>
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
      <span>{formatPublicRound(match.journee)}</span>
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
        <HomeTeam club={home} name={homeName} />
        <strong className="kf-home-card-score" aria-label={`Score ${homeScore} à ${awayScore}`}>
          <span className={homeWinner ? "winner" : ""}>{homeScore}</span>
          <i>–</i>
          <span className={awayWinner ? "winner" : ""}>{awayScore}</span>
        </strong>
        <HomeTeam club={away} name={awayName} align="right" />
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
        <HomeTeam club={home} name={homeName} />
        <strong>—</strong>
        <HomeTeam club={away} name={awayName} align="right" />
      </div>
      <HomeMatchMeta match={match} />
    </Link>
  );
}

function HomeLiveCard({ match, clubsById, saisonClubs, event }) {
  const home = findPublicClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const away = findPublicClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const homeName = textClub(clubsById, saisonClubs, match.equipe_domicile_id);
  const awayName = textClub(clubsById, saisonClubs, match.equipe_exterieur_id);
  const eventText = event ? `${formatMinute(event.minute, event.minute_additionnelle)} · ${labelEvenement(event)}` : "";

  return (
    <Link to={`/matchs/${match.id}`} className="kf-home-live-card">
      <div className="kf-home-live-top">
        <span><i /> LIVE</span>
        <span>{formatPublicRound(match.journee)}</span>
      </div>
      <div className="kf-home-live-teams">
        <HomeTeam club={home} name={homeName} />
        <strong>{displayValue(match.score_domicile)}–{displayValue(match.score_exterieur)}</strong>
        <HomeTeam club={away} name={awayName} align="right" />
      </div>
      {eventText && <p>{eventText}</p>}
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
  const status = match.statut === "en_cours"
    ? "EN DIRECT"
    : scorePublicVisible(match)
      ? "RÉSULTAT"
      : "À VENIR";

  return (
    <Link to={`/matchs/${match.id}`} className="kf-home-day-row">
      <span className="kf-home-day-time">{match.date_heure ? new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: "Africa/Bujumbura" }).format(new Date(match.date_heure)) : "—"}</span>
      <span className="kf-home-day-teams">
        <span><PublicClubLogo club={home} name={homeName} />{homeName}</span>
        <span><PublicClubLogo club={away} name={awayName} />{awayName}</span>
      </span>
      <span className={`kf-home-day-score${isLive(match) ? " live" : ""}`}>
        <small>{status}</small>
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
            return (
              <Link
                key={row.club_id ?? `${name}-${index}`}
                to={row.club_id ? `/clubs/${row.club_id}` : "/clubs"}
                className={`kf-home-rank-row${followed ? " followed" : ""}`}
                role="row"
              >
                <strong role="cell">{index + 1}</strong>
                <span className="kf-home-rank-club" role="cell"><PublicClubLogo club={club} name={name} /><span>{name}</span></span>
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
  const [evtsById, setEvtsById] = useState({});
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
      setEvtsById({});
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

      const lives = matches.filter(isLive);
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
    }

    charge();
    const timer = window.setInterval(charge, 30000);
    return () => {
      stop = true;
      window.clearInterval(timer);
    };
  }, [competition?.id, saison]);

  if (chargement) return <HomeSkeleton />;

  const lives = matchs.filter(isLive).sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const resultats = matchs.filter(isFinished).sort((a, b) => new Date(b.date_heure) - new Date(a.date_heure));
  const programmes = matchs.filter(isScheduled).sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const aujourdHui = todayCivil();
  const jour = addCivilDays(aujourdHui, jourOffset);
  const matchsDuJour = matchs
    .filter((match) => civilDate(match.date_heure) === jour)
    .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const installable = Boolean(installationEvent) && !installee;

  return (
    <section className="kf-home-page" aria-label="Accueil">
      <section className="kf-home-live-section" aria-labelledby="home-live-title">
        <div className="kf-home-section-head">
          <h2 id="home-live-title">LIVE</h2>
        </div>
        {lives.length === 0 ? (
          <p className="kf-home-empty">Aucun match en direct</p>
        ) : (
          <div className="kf-home-live-list">
            {lives.map((match) => <HomeLiveCard key={match.id} match={match} clubsById={clubsById} saisonClubs={saisonClubs} event={evtsById[match.id] || null} />)}
          </div>
        )}
      </section>

      <section className="kf-home-section" aria-labelledby="home-result-title">
        <div className="kf-home-section-head">
          <h2 id="home-result-title">Dernier résultat</h2>
          <Link to="/matchs">Tous les matchs <span aria-hidden="true">→</span></Link>
        </div>
        {resultats[0] ? <HomeResultCard match={resultats[0]} clubsById={clubsById} saisonClubs={saisonClubs} /> : <p className="kf-home-empty">Aucun résultat disponible pour le moment.</p>}
      </section>

      <section className="kf-home-section" aria-labelledby="home-next-title">
        <div className="kf-home-section-head">
          <h2 id="home-next-title">Prochain match</h2>
        </div>
        {programmes[0] ? <HomeUpcomingCard match={programmes[0]} clubsById={clubsById} saisonClubs={saisonClubs} /> : <p className="kf-home-empty">Aucun match programmé pour le moment</p>}
      </section>

      <section className="kf-home-section kf-home-day-schedule" aria-labelledby="home-day-title">
        <div className="kf-home-section-head">
          <div>
            <h2 id="home-day-title">Matchs du jour</h2>
            <p>{jourOffset === 0 ? "Aujourd’hui" : "Demain"}</p>
          </div>
          <div className="kf-home-day-nav" aria-label="Navigation des matchs par jour">
            <button type="button" aria-label="Afficher aujourd’hui" disabled={jourOffset === 0} onClick={() => setJourOffset(0)}>‹</button>
            <button type="button" aria-label="Afficher demain" disabled={jourOffset === 1} onClick={() => setJourOffset(1)}>›</button>
          </div>
        </div>
        {matchsDuJour.length === 0 ? <p className="kf-home-empty">Aucun match pour ce jour.</p> : matchsDuJour.map((match) => <HomeDayRow key={match.id} match={match} clubsById={clubsById} saisonClubs={saisonClubs} />)}
      </section>

      <HomeRanking classement={classement} clubsById={clubsById} saisonClubs={saisonClubs} saison={saison} />
      <HomeNews actualites={actualites} />
      {installable && <HomeInstall installationEvent={installationEvent} />}
    </section>
  );
}
