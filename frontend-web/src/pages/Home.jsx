import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { useKivu } from "../context.jsx";
import { AVenirLigne, LiveUne, TermineLigne } from "../components/LignesMatch.jsx";
import {
  addCivilDays,
  civilDate,
  dernierFaitLive,
  stripDemo,
  todayCivil,
} from "../display.js";
import {
  compareClassementRows,
  displayDifference,
  displayValue,
  findPublicClub,
  followedPublicClubId,
  PublicClubLogo,
} from "../components/PublicDesign.jsx";

function fusionner(a, b) {
  const map = new Map();
  for (const m of a || []) map.set(m.id, m);
  for (const m of b || []) map.set(m.id, m);
  return [...map.values()];
}

function dateEditoriale(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function prioriteEditoriale(item) {
  if (item.mise_en_avant) return "À la une";
  const age = item.date_publication ? Date.now() - new Date(item.date_publication).getTime() : -1;
  if (age >= 0 && age <= 7 * 24 * 60 * 60 * 1000) return "Récent";
  return "Actualité";
}

export default function Home() {
  const { saison, saisonClubs, clubsById, competition } = useKivu();
  const { user } = useAuth();
  const staff = user?.role === "organisateur" || user?.role === "admin";
  const [classement, setClassement] = useState([]);
  const [matchs, setMatchs] = useState([]);
  const [evtsById, setEvtsById] = useState({});
  const [actualites, setActualites] = useState([]);
  const [jourOffset, setJourOffset] = useState(0);
  const [maintenant, setMaintenant] = useState(() => Date.now());

  useEffect(() => {
    let stop = false;
    function chargeActualites() {
      api.actualites({ competitionId: competition?.id || "", limit: 50 })
        .then((rows) => { if (!stop) setActualites(rows || []); })
        .catch(() => { if (!stop) setActualites([]); });
    }
    chargeActualites();
    const timer = setInterval(chargeActualites, 30000);
    return () => { stop = true; clearInterval(timer); };
  }, [competition?.id]);

  useEffect(() => {
    const timer = setInterval(() => setMaintenant(Date.now()), 30000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!saison) return;
    let stop = false;
    function refresh() {
      api.classement(saison.id).then((c) => { if (!stop) setClassement(c); }).catch(() => { if (!stop) setClassement([]); });
      const pub = api.matchs(saison.id).catch(() => []);
      const gest = staff ? api.matchsGestion(saison.id).catch(() => []) : Promise.resolve([]);
      Promise.all([pub, gest]).then(async ([p, g]) => {
        if (stop) return;
        const rows = fusionner(p, g);
        setMatchs(rows);
        const lives = rows.filter((m) => m.statut === "en_cours" && !m.ended_at);
        if (!lives.length) {
          setEvtsById({});
          return;
        }
        const pairs = await Promise.all(
          lives.map((m) =>
            api.evenementsPublics(m.id)
              .then((evts) => [m.id, dernierFaitLive(evts)])
              .catch(() => [m.id, null]),
          ),
        );
        if (!stop) setEvtsById(Object.fromEntries(pairs));
      });
    }
    refresh();
    const t = setInterval(refresh, 5000);
    return () => {
      stop = true;
      clearInterval(t);
    };
  }, [saison, staff]);

  const lives = matchs.filter((m) => m.statut === "en_cours" && !m.ended_at);
  // Le bulletin reste limité à aujourd'hui / demain.
  // Un jour vide reste vide : aucun programme n'est inventé.
  const jour = jourOffset === 0 ? todayCivil() : addCivilDays(todayCivil(), 1);
  const programmes = matchs
    .filter((m) => m.statut === "programme")
    .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const aVenir = programmes.filter((m) => civilDate(m.date_heure) === jour);
  const termines = matchs
    .filter((m) => (m.statut === "termine" || m.statut === "valide") && civilDate(m.date_heure) === jour)
    .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));
  const apercu = [...classement].sort(compareClassementRows).slice(0, 5);
  const followedClubId = followedPublicClubId();
  const nomComp = competition ? stripDemo(competition.nom) : "";
  const actualiteAccueil = actualites.find((item) => item.mise_en_avant)
    || actualites.find((item) => {
      if (!item.date_publication) return false;
      const age = maintenant - new Date(item.date_publication).getTime();
      return age >= 0 && age < 10 * 60 * 1000;
    })
    || null;
  const numJ =
    lives[0]?.journee
    || aVenir[0]?.journee
    || termines[termines.length - 1]?.journee
    || programmes[programmes.length - 1]?.journee
    || 0;

  return (
    <>
      <header className="bulletin-hero">
        <div>
          <p className="kicker">Bulletin de compétition</p>
          <h1>Le terrain, sans détour.</h1>
          {nomComp && <p className="lead">{nomComp}</p>}
        </div>
        {numJ ? (
          <p className="hero-num">
            N° {String(numJ).padStart(2, "0")}
            <span>feuille officielle</span>
          </p>
        ) : null}
      </header>

      {lives.map((m) => (
        <LiveUne key={m.id} match={m} clubsById={clubsById} evt={evtsById[m.id] || null} />
      ))}

      {actualiteAccueil && (
        <section className="actualite-accueil" aria-labelledby="actualite-accueil-titre">
          <div className="actualite-accueil-en-tete">
            <div>
              <p className="kicker">📰 Actualités</p>
              <h2 id="actualite-accueil-titre">
                {actualiteAccueil.categorie === "annonce" ? "Communication officielle" : "Une information est disponible"}
              </h2>
            </div>
            <span className={`actualite-priorite ${actualiteAccueil.mise_en_avant ? "actualite-priorite-une" : ""}`}>
              {prioriteEditoriale(actualiteAccueil)}
            </span>
          </div>
          <Link to={`/actualites/${actualiteAccueil.id}`} className="actualite-accueil-carte">
            {actualiteAccueil.image_principale_url ? (
              <img src={actualiteAccueil.image_principale_url} alt="" />
            ) : (
              <div className="actualite-accueil-image-vide">KivuFoot</div>
            )}
            <div>
              <p className="actualite-accueil-date">{dateEditoriale(actualiteAccueil.date_publication)}</p>
              {actualiteAccueil.categorie === "annonce" && <p className="actualite-accueil-source">Source : Comité d’Organisation</p>}
              <h3>{actualiteAccueil.titre}</h3>
              {actualiteAccueil.competition_nom && <p>{actualiteAccueil.competition_nom}</p>}
              <strong>Lire l’actualité →</strong>
            </div>
          </Link>
          <Link className="actualite-accueil-toutes" to="/actualites">Voir toutes les actualités</Link>
        </section>
      )}

      <section>
        <div className="jour-barre">
          <h2>Le bulletin</h2>
          <Link className="bulletin-tous" to="/matchs">Tous les matchs</Link>
        </div>
        <div className="jour-barre jour-barre-sub">
          <h3>À venir</h3>
          <div className="jour-nav" aria-label="Navigation des prochains matchs">
            <button
              type="button"
              aria-label="Afficher les matchs d'aujourd'hui"
              disabled={jourOffset === 0}
              onClick={() => setJourOffset(0)}
            >
              ‹
            </button>
            <span>{jourOffset === 0 ? "Aujourd'hui" : "Demain"}</span>
            <button
              type="button"
              aria-label="Afficher les matchs de demain"
              disabled={jourOffset === 1}
              onClick={() => setJourOffset(1)}
            >
              ›
            </button>
          </div>
        </div>
        {aVenir.length === 0 && <p className="empty">Pas de match prévu ce jour.</p>}
        {aVenir.map((m) => (
          <AVenirLigne key={m.id} match={m} clubsById={clubsById} />
        ))}
      </section>

      <section>
        <div className="section-head">
          <h2>Terminés</h2>
        </div>
        {termines.length === 0 && <p className="empty">Pas encore de match terminé ce jour.</p>}
        {termines.map((m) => (
          <TermineLigne key={m.id} match={m} clubsById={clubsById} />
        ))}
      </section>

      <section className="kf-public-home-ranking">
        <div className="kf-public-home-ranking-head">
          <div>
            <h2>Mini-classement</h2>
            <p>{saison?.nom || "—"}</p>
          </div>
          <Link to="/classement">Classement complet <span aria-hidden="true">→</span></Link>
        </div>
        {classement.length === 0 && (
          <p className="empty">Le classement se calcule sur les matchs validés.</p>
        )}
        {apercu.length > 0 && (
          <div className="kf-public-mini-rank" role="table" aria-label="Mini-classement">
            <div className="kf-public-mini-rank-head" role="row">
              <span role="columnheader">#</span>
              <span role="columnheader">Club</span>
              <span role="columnheader">Pts</span>
              <span role="columnheader">J</span>
              <span role="columnheader">Diff</span>
            </div>
            {apercu.map((ligne, index) => {
              const club = findPublicClub(clubsById, saisonClubs, ligne.club_id);
              const followed = followedClubId !== null && Number(ligne.club_id) === followedClubId;
              const name = stripDemo(ligne.club_nom || club?.nom || "—");
              return (
                <Link
                  key={ligne.club_id ?? index}
                  to={ligne.club_id ? `/clubs/${ligne.club_id}` : "/clubs"}
                  className={`kf-public-mini-rank-row${followed ? " followed" : ""}`}
                  role="row"
                >
                  <strong role="cell">{index + 1}</strong>
                  <span className="kf-public-mini-rank-club" role="cell">
                    <PublicClubLogo club={club} name={name} />
                    <span>{name}</span>
                  </span>
                  <strong role="cell">{displayValue(ligne.points)}</strong>
                  <span role="cell">{displayValue(ligne.matchs_joues)}</span>
                  <span role="cell">{displayDifference(ligne.difference_buts)}</span>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </>
  );
}
