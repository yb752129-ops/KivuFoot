import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { useKivu } from "../../context.jsx";
import { stripDemo } from "../../display.js";
import { AVenirLigne } from "../../components/LignesMatch.jsx";
import { assurerSaison, isoDepuisDateHeure } from "./saison.js";

const GROUPES = ["A", "B", "C", "D"];

export default function OrgaCalendrier() {
  const { user } = useAuth();
  const {
    saison, saisonClubs, clubsById, competition,
    rechargerCompetitions, choisirCompetition, chargerClubsSaison,
  } = useKivu();
  const bureau = user?.role === "organisateur" || user?.role === "admin";
  const equipes = saisonClubs ?? [];
  const [matchs, setMatchs] = useState([]);
  const [domId, setDomId] = useState("");
  const [extId, setExtId] = useState("");
  const [dateMatch, setDateMatch] = useState("");
  const [heureMatch, setHeureMatch] = useState("");
  const [stadeMatch, setStadeMatch] = useState("");
  const [journee, setJournee] = useState("");
  const [phase, setPhase] = useState("poule");
  const [groupe, setGroupe] = useState("");
  const [sourceDomId, setSourceDomId] = useState("");
  const [sourceExtId, setSourceExtId] = useState("");
  const [appariementManuelOfficiel, setAppariementManuelOfficiel] = useState(false);
  const [reglements, setReglements] = useState([]);
  const [modeEgalite, setModeEgalite] = useState("tirs_au_but_apres_90");
  const [sourceDecision, setSourceDecision] = useState("");
  const [regleBusy, setRegleBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    if (!saison) {
      setMatchs([]);
      setReglements([]);
      return;
    }
    const [ms, rules] = await Promise.all([
      api.matchsGestion(saison.id, 100).catch(() => []),
      api.reglements({ saisonId: saison.id }).catch(() => []),
    ]);
    setMatchs(ms || []);
    setReglements(rules || []);
    const active = (rules || []).find((rule) => rule.statut === "actif");
    const configuredMode = active?.configuration?.match?.mode_egalite_eliminatoire;
    setModeEgalite(configuredMode === "prolongations_2x15" ? "prolongations_2x15" : "tirs_au_but_apres_90");
  }

  useEffect(() => {
    setAppariementManuelOfficiel(false);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [saison]);

  if (!bureau) return <Navigate to="/orga/matchs" replace />;

  const domicile = equipes.find((c) => String(c.id) === String(domId));
  const exterieur = equipes.find((c) => String(c.id) === String(extId));
  const groupeAuto =
    phase === "poule" && domicile?.groupe && domicile.groupe === exterieur?.groupe
      ? domicile.groupe
      : "";
  const groupesDifferents =
    phase === "poule" && domicile?.groupe && exterieur?.groupe && domicile.groupe !== exterieur.groupe;
  const groupeIncomplet =
    phase === "poule" && domicile && exterieur && (!domicile.groupe || !exterieur.groupe);
  const phaseSource = { quart: "barrage", demi: "quart", finale: "demi" }[phase];
  const sourcesUtilisees = new Set(
    matchs.flatMap((match) => [match.source_match_domicile_id, match.source_match_exterieur_id].filter(Boolean).map(Number)),
  );
  const sourcesDisponibles = phaseSource
    ? matchs.filter((match) => match.phase === phaseSource && !sourcesUtilisees.has(Number(match.id)))
    : [];
  const reglementActif = reglements.find((rule) => rule.statut === "actif") || null;
  const libelleSource = (match) => {
    const dom = stripDemo(clubsById[match.equipe_domicile_id]?.nom || "Équipe à déterminer");
    const ext = stripDemo(clubsById[match.equipe_exterieur_id]?.nom || "Équipe à déterminer");
    return `Match #${match.id} · ${dom} – ${ext} · ${match.statut}`;
  };

  async function programmer(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const s = await assurerSaison({
        saison, competition, api, rechargerCompetitions, choisirCompetition, chargerClubsSaison,
      });
      const d = sourceDomId ? null : (domId ? Number(domId) : null);
      const x = sourceExtId ? null : (extId ? Number(extId) : null);
      const sourceDom = sourceDomId ? Number(sourceDomId) : null;
      const sourceExt = sourceExtId ? Number(sourceExtId) : null;
      if ((!d && !sourceDom) || (!x && !sourceExt)) throw new Error("Choisissez une équipe ou un match source pour chaque côté.");
      if (appariementManuelOfficiel && (phase !== "quart" || !d || !x || sourceDom || sourceExt)) {
        throw new Error("L'exception officielle exige deux équipes sélectionnées directement en quart de finale.");
      }
      if (d && x && d === x) throw new Error("Une équipe ne peut pas jouer contre elle-même.");
      if (phase === "poule" && groupesDifferents) {
        throw new Error("Un match de poule doit opposer deux équipes du même groupe officiel.");
      }
      if (phase === "poule" && !groupeAuto) {
        throw new Error("Affectez d'abord un groupe officiel aux deux équipes.");
      }
      const equipeDomicile = d ? (equipes.find((c) => c.id === d) || clubsById[d]) : null;
      await api.creerMatch({
        saison_id: s.id,
        journee: journee.trim().slice(0, 20) || null,
        phase: phase || "poule",
        groupe: phase === "poule" ? groupeAuto : groupe || null,
        date_heure: phase === "barrage" && !dateMatch && !heureMatch
          ? null
          : isoDepuisDateHeure(dateMatch, heureMatch),
        stade: stadeMatch.trim() || equipeDomicile?.stade || null,
        equipe_domicile_id: d,
        equipe_exterieur_id: x,
        source_match_domicile_id: sourceDom,
        source_match_exterieur_id: sourceExt,
        appariement_manuel_officiel: appariementManuelOfficiel,
      });
      setMsg("Match programmé. Il apparaît dans À venir côté public.");
      setDomId("");
      setExtId("");
      setSourceDomId("");
      setSourceExtId("");
      setAppariementManuelOfficiel(false);
      setStadeMatch("");
      setJournee("");
      setGroupe("");
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function enregistrerReglement() {
    if (regleBusy) return;
    setRegleBusy(true);
    setErr("");
    setMsg("");
    try {
      const s = await assurerSaison({
        saison, competition, api, rechargerCompetitions, choisirCompetition, chargerClubsSaison,
      });
      const competitionId = Number(competition?.id || s.competition_id);
      if (!competitionId) throw new Error("La compétition de cette saison est introuvable.");
      const modeActif = reglementActif?.configuration?.match?.mode_egalite_eliminatoire || "tirs_au_but_apres_90";
      if (reglementActif && modeActif === modeEgalite) {
        throw new Error("Ce mode est déjà actif pour cette édition.");
      }
      const base = reglementActif?.configuration && typeof reglementActif.configuration === "object"
        ? reglementActif.configuration
        : {};
      const version = Math.max(0, ...reglements.map((rule) => Number(rule.version) || 0)) + 1;
      const brouillon = await api.creerReglement({
        competition_id: competitionId,
        saison_id: s.id,
        version,
        configuration: {
          ...base,
          mode_moteur: base.mode_moteur || "report_only",
          match: { ...(base.match || {}), mode_egalite_eliminatoire: modeEgalite },
        },
        reference_decision: sourceDecision.trim() || null,
      });
      await api.activerReglement(brouillon.id);
      setSourceDecision("");
      setMsg(`Règlement v${version} activé. Les nouveaux matchs seront liés à cette version; les matchs déjà programmés conservent leur règlement.`);
      await load();
    } catch (ex) {
      setErr(ex.message || "Impossible d’activer le règlement.");
    } finally {
      setRegleBusy(false);
    }
  }

  const aVenir = matchs
    .filter((m) => m.statut === "programme")
    .sort((a, b) => {
      if (!a.date_heure && !b.date_heure) return Number(a.id || 0) - Number(b.id || 0);
      if (!a.date_heure) return 1;
      if (!b.date_heure) return -1;
      return new Date(a.date_heure) - new Date(b.date_heure);
    });

  return (
    <section className="hero">
      <h1>Calendrier</h1>
      <p className="lead">Un match programmé doit se voir sur l’Accueil public.</p>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}

      {equipes.length < 2 ? (
        <p className="empty">Inscrivez au moins deux équipes. <Link to="/orga/equipes">Équipes</Link></p>
      ) : (
        <form className="compte-form" onSubmit={programmer}>
          <label className="field">
            Domicile
            <select value={domId} disabled={Boolean(sourceDomId)} onChange={(e) => { setDomId(e.target.value); setAppariementManuelOfficiel(false); if (e.target.value) setSourceDomId(""); }} required>
              <option value="">—</option>
              {equipes.map((c) => (
                <option key={c.id} value={c.id}>{stripDemo(c.nom)}</option>
              ))}
            </select>
          </label>
          <label className="field">
            Extérieur
            <select value={extId} disabled={Boolean(sourceExtId)} onChange={(e) => { setExtId(e.target.value); setAppariementManuelOfficiel(false); if (e.target.value) setSourceExtId(""); }} required>
              <option value="">—</option>
              {equipes.map((c) => (
                <option key={c.id} value={c.id}>{stripDemo(c.nom)}</option>
              ))}
            </select>
          </label>
          {phaseSource && (
            <div className="phase-box">
              <p className="lead">
                Pour réutiliser un match du tour précédent ({phaseSource}), sélectionnez son vainqueur comme source explicite.
                Aucun appariement n’est déduit automatiquement.
              </p>
              <div className="comp-grid">
                <label className="field">
                  Domicile · source du tour précédent
                  <select value={sourceDomId} onChange={(e) => { setSourceDomId(e.target.value); if (e.target.value) { setDomId(""); setAppariementManuelOfficiel(false); } }}>
                    <option value="">Équipe nommée directement</option>
                    {sourcesDisponibles.map((match) => <option key={match.id} value={match.id}>{libelleSource(match)}</option>)}
                  </select>
                </label>
                <label className="field">
                  Extérieur · source du tour précédent
                  <select value={sourceExtId} onChange={(e) => { setSourceExtId(e.target.value); if (e.target.value) { setExtId(""); setAppariementManuelOfficiel(false); } }}>
                    <option value="">Équipe nommée directement</option>
                    {sourcesDisponibles.map((match) => <option key={match.id} value={match.id}>{libelleSource(match)}</option>)}
                  </select>
                </label>
              </div>
              {phase === "quart" && (
                <>
                  <label className="checkbox-line">
                    <input
                      type="checkbox"
                      checked={appariementManuelOfficiel}
                      disabled={!domId || !extId || Boolean(sourceDomId || sourceExtId)}
                      onChange={(e) => setAppariementManuelOfficiel(e.target.checked)}
                    />
                    <span>Exception officielle : respecter le tirage au sort ou une décision de la compétition</span>
                  </label>
                  <p className="muted small">
                    À utiliser uniquement pour une affiche de quart confirmée officiellement. Une équipe éliminée reste refusée; le vainqueur d’un barrage doit avoir un résultat validé.
                  </p>
                </>
              )}
              {sourcesDisponibles.length === 0 && <p className="muted small">Aucun match de phase {phaseSource} disponible comme source pour l’instant.</p>}
            </div>
          )}
          <div className="comp-grid">
            <label className="field">
              Date
              <input type="date" value={dateMatch} onChange={(e) => setDateMatch(e.target.value)} required={phase !== "barrage"} />
            </label>
            <label className="field">
              Heure
              <input type="time" value={heureMatch} onChange={(e) => setHeureMatch(e.target.value)} required={phase !== "barrage"} />
            </label>
          </div>
          {phase === "barrage" && (
            <p className="lead">Pour un barrage, laissez les deux champs vides si le coup d’envoi n’est pas fixé. Les deux équipes officielles restent obligatoires.</p>
          )}
          <label className="field">
            Stade
            <input
              value={stadeMatch}
              onChange={(e) => setStadeMatch(e.target.value)}
              placeholder={domicile?.stade || "à compléter"}
            />
          </label>
          <label className="field">
            Phase
            <select value={phase} onChange={(e) => { setPhase(e.target.value); setSourceDomId(""); setSourceExtId(""); setAppariementManuelOfficiel(false); }}>
            <option value="poule">Poule</option>
            <option value="barrage">Barrage</option>
            <option value="quart">Quart de finale</option>
              <option value="demi">Demi-finale</option>
              <option value="finale">Finale</option>
            </select>
          </label>
          <label className="field">
            Groupe
            <select
              value={phase === "poule" ? groupeAuto : groupe}
              onChange={(e) => setGroupe(e.target.value)}
              disabled={phase === "poule"}
            >
              {phase === "poule" ? (
                <option value="">{groupeAuto ? `Groupe ${groupeAuto} — déduit` : "Affecter les deux équipes"}</option>
              ) : (
                <>
                  <option value="">Sans groupe</option>
                  {GROUPES.map((g) => <option key={g} value={g}>Groupe {g}</option>)}
                </>
              )}
            </select>
          </label>
          {groupesDifferents && <p className="erreur">Les deux équipes sont dans des groupes officiels différents.</p>}
          {groupeIncomplet && <p className="erreur">Un groupe officiel manque pour l’une des équipes.</p>}
          <label className="field">
            Journée
            <input value={journee} onChange={(e) => setJournee(e.target.value)} maxLength={20} placeholder="ex. J1" />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "…" : "Programmer le match"}
          </button>
        </form>
      )}

      {saison && (
        <section className="phase-box" aria-label="Règlement des matchs éliminatoires">
          <p className="kicker">Règlement de l’édition</p>
          <h2>Égalité en phase éliminatoire</h2>
          <p className="lead">
            {reglementActif
              ? `Version active v${reglementActif.version}. Les nouveaux matchs seront rattachés à cette version.`
              : "Aucun règlement actif : les matchs historiques conservent le comportement tirs au but après 90 minutes."}
            {" "}Les matchs déjà programmés gardent leur version existante.
          </p>
          <label className="field">
            Mode de décision
            <select value={modeEgalite} onChange={(e) => setModeEgalite(e.target.value)}>
              <option value="tirs_au_but_apres_90">Tirs au but directement après 90 minutes</option>
              <option value="prolongations_2x15">2 × 15 minutes, puis tirs au but si l’égalité persiste</option>
            </select>
          </label>
          <label className="field">
            Référence de décision (facultative)
            <input value={sourceDecision} onChange={(e) => setSourceDecision(e.target.value)} maxLength={255} placeholder="Décision / référence du règlement" />
          </label>
          <button className="btn" type="button" disabled={regleBusy} onClick={enregistrerReglement}>
            {regleBusy ? "Activation…" : `Créer et activer la version ${Math.max(0, ...reglements.map((rule) => Number(rule.version) || 0)) + 1}`}
          </button>
        </section>
      )}

      <div className="section-head">
        <h2>À venir</h2>
      </div>
      {aVenir.length === 0 && <p className="empty">Aucun match programmé.</p>}
      {aVenir.map((m) => (
        <AVenirLigne key={m.id} match={m} clubsById={clubsById} to={`/orga/matchs/${m.id}`} />
      ))}
    </section>
  );
}
