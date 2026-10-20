import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import Scoreboard from "../components/Scoreboard.jsx";
import FeuilleApercu from "../components/FeuilleApercu.jsx";
import FeuilleMatch from "../components/FeuilleMatch.jsx";
import { LiveUne } from "../components/LignesMatch.jsx";
import { scorePublicVisible } from "../components/PublicDesign.jsx";
import { startVisibleRefresh } from "../liveRefresh.js";
import { grouperFaits, journeeTitre, statsDesFaits, stripDemo } from "../display.js";

function formatDetailDate(iso) {
  if (!iso) return "";
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "short",
    day: "numeric",
    month: "long",
    timeZone: "Africa/Lubumbashi",
  }).format(new Date(iso));
}

function pourcentageValide(value) {
  if (value === null || value === undefined || value === "") return false;
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 && n <= 100;
}

const ONGLETS = [
  { id: "apercu", label: "Événements" },
  { id: "stats", label: "Statistiques" },
  { id: "compo", label: "Compositions" },
];

function compositionPubliee(compo) {
  if (!compo) return false;
  return [compo.domicile, compo.exterieur].some((bloc) => (
    bloc
    && (bloc.formation
      || bloc.staff?.nom_complet
      || (Array.isArray(bloc.titulaires) && bloc.titulaires.length > 0)
      || (Array.isArray(bloc.banc) && bloc.banc.length > 0))
  ));
}

export default function MatchDetail() {
  const { id } = useParams();
  const { clubsById } = useKivu();
  const [match, setMatch] = useState(null);
  const [evts, setEvts] = useState([]);
  const [joueurs, setJoueurs] = useState({});
  const [compo, setCompo] = useState(null);
  const [possession, setPossession] = useState(null);
  const [moi, setMoi] = useState(null);
  const [documentBusy, setDocumentBusy] = useState(false);
  const [documentMsg, setDocumentMsg] = useState("");
  const [onglet, setOnglet] = useState("apercu");
  const [err, setErr] = useState("");

  async function genererPDF() {
    setDocumentBusy(true);
    setDocumentMsg("");
    try {
      const document = await api.genererDocumentMatch(id);
      const publie = document?.statut === "publie" && document?.url;
      if (publie) {
        setDocumentMsg("PDF officiel prêt au téléchargement.");
      } else {
        setDocumentMsg(document?.message_erreur || "Le PDF n’a pas pu être publié.");
      }
    } catch (e) {
      setDocumentMsg(e.message || "Génération du PDF impossible.");
    } finally {
      setDocumentBusy(false);
    }
  }

  async function load() {
    const m = await api.match(id);
    const [e, joueursDom, joueursExt, p, possessionPublique] = await Promise.all([
      api.evenementsPublics(id).catch(() => []),
      api.joueurs(m.equipe_domicile_id).catch(() => []),
      api.joueurs(m.equipe_exterieur_id).catch(() => []),
      api.composition(id).catch(() => null),
      api.possession(id).catch(() => ({ disponible: false, message: "Possession non disponible" })),
    ]);
    const js = [...(joueursDom || []), ...(joueursExt || [])];
    setErr("");
    setMatch(m);
    setEvts(e || []);
    setJoueurs(Object.fromEntries(js.map((j) => [j.id, j])));
    setCompo(p || null);
    setPossession(possessionPublique || null);
    api.me().then(setMoi).catch(() => setMoi(null));
  }

  useEffect(() => {
    let stop = false;
    setErr("");
    setMatch(null);
    const stopRefresh = startVisibleRefresh(async () => {
      try {
        await load();
      } catch (e) {
        if (!stop) setErr(e.message || "Match introuvable.");
      }
    }, 10000);
    return () => {
      stop = true;
      stopRefresh();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (err) {
    return (
      <section className="hero">
        <p className="kicker"><Link to="/matchs">← Matchs</Link></p>
        <p className="erreur">{err}</p>
      </section>
    );
  }
  if (!match) return <p className="empty">Chargement…</p>;

  const home = clubsById[match.equipe_domicile_id];
  const away = clubsById[match.equipe_exterieur_id];
  const live = match.statut === "en_cours" && !match.ended_at;
  const nom = (jid) => joueurs[jid]?.nom_complet || "à compléter";
  const faits = grouperFaits(evts);
  const stats = statsDesFaits(evts);
  const scoreVisible = scorePublicVisible(match);
  const compositionVisible = compositionPubliee(compo);
  const possessionDisponible = Boolean(
    possession?.disponible
    && pourcentageValide(possession.pourcentage_a)
    && pourcentageValide(possession.pourcentage_b),
  );
  const possessionA = possessionDisponible ? Number(possession.pourcentage_a) : null;
  const possessionB = possessionDisponible ? Number(possession.pourcentage_b) : null;
  const possessionAdminView = Boolean(moi && ["admin", "organisateur"].includes(moi.role));

  return (
    <section className="hero">
      <p className="match-detail-back"><Link to="/matchs">← Matchs</Link></p>
      <p className="match-detail-meta">
        {journeeTitre(match.journee)}
        {match.date_heure ? ` · ${formatDetailDate(match.date_heure)}` : ""}
      </p>

      {live ? (
        <LiveUne match={match} clubsById={clubsById} />
      ) : (
        <div className="sheet mc-score" style={{ marginTop: "0.85rem" }}>
          <Scoreboard match={match} clubsById={clubsById} />
        </div>
      )}
      {possessionAdminView && match.statut === "valide" && <p className="stamp">Validé</p>}
      {moi && ["admin", "organisateur"].includes(moi.role) && match.statut === "valide" && (
        <section className="sheet document-actions" aria-label="Document officiel">
          <p className="kicker">Document officiel</p>
          <p className="muted small">Générez ou actualisez le PDF à partir des données validées de ce match.</p>
          <button className="btn btn-primary" type="button" disabled={documentBusy} onClick={genererPDF}>
            {documentBusy ? "Génération…" : "Générer le PDF officiel"}
          </button>
          {documentMsg && <p className="empty">{documentMsg}</p>}
        </section>
      )}
      {match.forfait && <p className="lead">Forfait</p>}
      {match.note_officielle && (
        <aside className="match-note" aria-label="Note officielle">
          <p className="kicker">Note officielle</p>
          <p>{match.note_officielle}</p>
          {match.resultat_retroactif && (
            <p className="match-note-followup">
              {match.buteurs_a_verifier
                ? "Les buteurs sont enregistrés auprès des organisateurs et seront ajoutés après vérification."
                : "Les buteurs vérifiés ont été ajoutés à la fiche du match sans modifier le score officiel."}
            </p>
          )}
        </aside>
      )}

      <div className="mc-tabs" role="tablist">
        {ONGLETS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={onglet === t.id}
            className={onglet === t.id ? "on" : ""}
            onClick={() => setOnglet(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {onglet === "apercu" && (
        <FeuilleApercu faits={faits} nom={nom} match={match} />
      )}

      {onglet === "stats" && (
        scoreVisible ? (
          <>
          <table className="table stats-feuille table-accueil">
          <thead>
            <tr>
              <th>
                <span className="stats-team-heading">
                  <span className="stats-team-dot stats-team-dot-home" aria-hidden="true" />
                  <span>{stripDemo(home?.nom) || "Domicile"}</span>
                </span>
              </th>
              <th />
              <th>
                <span className="stats-team-heading stats-team-heading-away">
                  <span>{stripDemo(away?.nom) || "Extérieur"}</span>
                  <span className="stats-team-dot stats-team-dot-away" aria-hidden="true" />
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr className="stats-possession-row">
              <td className={`stats-possession-value${possessionA > possessionB ? " is-high" : ""}`}>
                {possessionDisponible ? `${possessionA} %` : "—"}
              </td>
              <td>Possession</td>
              <td className={`stats-possession-value${possessionB > possessionA ? " is-high" : ""}`}>
                {possessionDisponible ? `${possessionB} %` : "—"}
              </td>
            </tr>
            {possessionDisponible && (
              <tr className="stats-possession-bar-row" aria-label="Répartition de la possession">
                <td colSpan={3}>
                  <div className="stats-possession-bar" aria-hidden="true">
                    <span style={{ width: `${possessionA}%` }} />
                    <span style={{ width: `${possessionB}%` }} />
                  </div>
                </td>
              </tr>
            )}
            <tr>
              <td>{match.score_domicile}</td>
              <td>Buts</td>
              <td>{match.score_exterieur}</td>
            </tr>
            <tr>
              <td>{stats.domicile.jaunes}</td>
              <td>Jaunes</td>
              <td>{stats.exterieur.jaunes}</td>
            </tr>
            <tr>
              <td>{stats.domicile.rouges}</td>
              <td>Rouges</td>
              <td>{stats.exterieur.rouges}</td>
            </tr>
            <tr>
              <td>{stats.domicile.penalties_rates}</td>
              <td>Penalties ratés</td>
              <td>{stats.exterieur.penalties_rates}</td>
            </tr>
          </tbody>
        </table>
          </>
        ) : (
          <p className="empty">Les statistiques seront disponibles après le coup d'envoi.</p>
        )
      )}

      {onglet === "compo" && (
        <>
          {compositionVisible ? (
            <FeuilleMatch compo={compo} logos={{ domicile: home?.logo_url, exterieur: away?.logo_url }} />
          ) : (
            <p className="empty">Compositions pas encore publiées.</p>
          )}
          {moi && moi.club_id && moi.club_id === match.equipe_domicile_id || moi && moi.club_id && moi.club_id === match.equipe_exterieur_id ? (
            <Link className="feuille-lien-editeur" to={`/club/matchs/${id}/composition`}>Préparer la feuille de mon équipe</Link>
          ) : null}
        </>
      )}
    </section>
  );
}
