import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, clearTokens } from "../api.js";
import Chrono from "../components/Chrono.jsx";
import { clubName, useKivu } from "../context.jsx";
import { civilDate, clockFromMatch, formatHeure, formatMinute, grouperFaits, labelEvenement, MOTIF_REFUS, periodeLabel, splitMinute, stripDemo } from "../display.js";
import { isoDepuisDateHeure, STATUT_MATCH } from "./orga/saison.js";

const LABELS = {
  but: "But",
  carton_jaune: "Jaune",
  carton_rouge: "Rouge",
  but_contre_son_camp: "CSC",
  penalty: "Penalty",
  remplacement: "Remplacement",
  passe_decisive: "Passe décisive",
};

const STATUT_FAIT = {
  en_attente: "En attente",
  valide: "Validé",
  rejete: "Rejeté",
};

const TYPES = [
  { value: "but", label: "But" },
  { value: "but_contre_son_camp", label: "CSC" },
  { value: "penalty", label: "Penalty" },
  { value: "carton_jaune", label: "Jaune" },
  { value: "carton_rouge", label: "Rouge" },
  { value: "remplacement", label: "Remplacement" },
];

const NOTE_RETROACTIVE_DEFAULT =
  "Match joué après confirmation de l’administration alors qu’il avait initialement été annoncé comme annulé. "
  + "Résultat officiel : le score saisi ci-dessus. Les buteurs sont bien enregistrés auprès des organisateurs.";

function noteRetroactiveAvecScore(scoreDom, scoreExt) {
  return NOTE_RETROACTIVE_DEFAULT.replace("le score saisi ci-dessus", `${scoreDom}–${scoreExt}`);
}

const TYPE_SENS = {
  but: "But de jeu. Tête ou coup franc : encore un but. Passeur optionnel. 47 = 45+2, 94 = 90+4.",
  but_contre_son_camp: "CSC. Crédité à l’adversaire. Pas au joueur.",
  penalty: "Penalty de jeu. Marqué = un but, pas un second fait « but ». Raté = à côté, arrêté ou poteau. Si le tir est à retirer, n’enregistre pas encore. Ce n’est pas une séance de tirs au but.",
  carton_jaune: "Jaune. Un 2e jaune validé crée le rouge tout seul. Ne saisis pas le rouge à part.",
  carton_rouge: "Rouge direct. Le rouge du 2e jaune est créé tout seul.",
  remplacement: "Un sortant, un entrant. Un double = deux enregistrements à la même minute.",
};

export default function OrgaMatch({ backTo = "/orga/matchs", mode = "orga" } = {}) {
  const { id } = useParams();
  const nav = useNavigate();
  const { clubsById } = useKivu();
  const collecteur = mode === "collecteur";
  const [match, setMatch] = useState(null);
  const [controleEffectif, setControleEffectif] = useState(null);
  const [evts, setEvts] = useState([]);
  const [joueursDom, setJoueursDom] = useState([]);
  const [joueursExt, setJoueursExt] = useState([]);
  const [parts, setParts] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [type, setType] = useState("but");
  const [cote, setCote] = useState("domicile");
  const [joueurId, setJoueurId] = useState("");
  const [secondaireId, setSecondaireId] = useState("");
  const [resultat, setResultat] = useState("marque");
  const [phaseSel, setPhaseSel] = useState("poule");
  const [groupeSel, setGroupeSel] = useState("");
  const [dateProg, setDateProg] = useState("");
  const [heureProg, setHeureProg] = useState("");
  const [stadeProg, setStadeProg] = useState("");
  const [retroScoreDom, setRetroScoreDom] = useState("");
  const [retroScoreExt, setRetroScoreExt] = useState("");
  const [retroMotif, setRetroMotif] = useState("");
  const [retroNote, setRetroNote] = useState(NOTE_RETROACTIVE_DEFAULT);
  const [buteursRetro, setButeursRetro] = useState([]);
  const [minute, setMinute] = useState("0");
  const [now, setNow] = useState(Date.now());
  const [compDraft, setCompDraft] = useState({});
  const [autre, setAutre] = useState(false);
  const [refusId, setRefusId] = useState(null);
  const [refusMotif, setRefusMotif] = useState("hors_jeu");
  const [rejetId, setRejetId] = useState(null);
  const [rejetCommentaire, setRejetCommentaire] = useState("");
  const busyRef = useRef(false);

  const home = stripDemo(clubName(clubsById, match?.equipe_domicile_id));
  const away = stripDemo(clubName(clubsById, match?.equipe_exterieur_id));
  const joueurs = cote === "exterieur" ? joueursExt : joueursDom;
  const periode = match?.periode || (match?.statut === "en_cours" ? "1" : null);
  const enCours = match?.statut === "en_cours";
  const ht = enCours && periode === "mi_temps";
  const running = enCours && !ht;

  useEffect(() => {
    if (match) {
      setPhaseSel(match.phase || "poule");
      setGroupeSel(match.groupe || "");
      setDateProg(civilDate(match.date_heure));
      setHeureProg(formatHeure(match.date_heure));
      setStadeProg(match.stade || "");
      setRetroScoreDom(String(match.score_domicile ?? ""));
      setRetroScoreExt(String(match.score_exterieur ?? ""));
      setRetroMotif(match.motif_resultat_retroactif || "");
      setRetroNote(match.note_officielle || NOTE_RETROACTIVE_DEFAULT);
      if (match.resultat_retroactif && match.buteurs_a_verifier) {
        const total = (match.score_domicile || 0) + (match.score_exterieur || 0);
        setButeursRetro(
          Array.from({ length: total }, (_, index) => ({
            equipe_concernee: index < (match.score_domicile || 0) ? "domicile" : "exterieur",
            joueur_id: "",
            minute: "",
          })),
        );
      } else {
        setButeursRetro([]);
      }
    }
  }, [match]);

  async function enregistrerProgrammation(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const m = await api.modifierProgrammation(match.id, {
        date_heure: isoDepuisDateHeure(dateProg, heureProg),
        stade: stadeProg.trim() || null,
      });
      setMatch(m);
      setMsg("Programmation modifiée.");
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function enregistrerResultatRetroactif(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const scoreDom = Number(retroScoreDom);
      const scoreExt = Number(retroScoreExt);
      if (!Number.isInteger(scoreDom) || scoreDom < 0 || !Number.isInteger(scoreExt) || scoreExt < 0) {
        throw new Error("Saisissez deux scores entiers positifs ou nuls.");
      }
      const resultat = await api.resultatRetroactif(id, {
        score_domicile: scoreDom,
        score_exterieur: scoreExt,
        motif: retroMotif,
        note_officielle: retroNote.includes("le score saisi ci-dessus")
          ? noteRetroactiveAvecScore(scoreDom, scoreExt)
          : retroNote,
      });
      setMatch(resultat);
      setMsg("Résultat rétrospectif enregistré et validé. Le match est verrouillé.");
      await load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function annulerResultatRetroactif() {
    const motif = window.prompt(
      "Motif obligatoire : pourquoi le résultat rétroactif doit-il être révoqué ?",
      "Le match a finalement été déclaré non joué et doit être reprogrammé aujourd'hui.",
    );
    if (motif === null) return;
    if (motif.trim().length < 10) {
      setErr("Le motif doit contenir au moins 10 caractères.");
      return;
    }
    if (!window.confirm("Révoquer le 1–1 publié et déverrouiller ce match ? Cette action sera auditée.")) return;
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      await api.annulerResultatRetroactif(id, { motif: motif.trim() });
      setMsg("Résultat rétroactif révoqué. Le match est de nouveau programmable ; reprogrammez-le ensuite.");
      await load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function enregistrerButeursVerifies(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const buteurs = buteursRetro.map((buteur) => {
        if (!buteur.joueur_id) throw new Error("Sélectionnez tous les buteurs vérifiés.");
        return {
          joueur_id: Number(buteur.joueur_id),
          equipe_concernee: buteur.equipe_concernee,
          minute: buteur.minute === "" ? null : Number(buteur.minute),
        };
      });
      await api.buteursVerifies(id, { buteurs });
      setMsg("Les buteurs vérifiés ont été ajoutés sans modifier le score officiel.");
      await load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  function modifierButeur(index, champ, valeur) {
    setButeursRetro((liste) => liste.map((buteur, i) => (
      i === index
        ? { ...buteur, [champ]: valeur, ...(champ === "equipe_concernee" ? { joueur_id: "" } : {}) }
        : buteur
    )));
  }

  async function enregistrerPhase() {
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const m = await api.majPhase(match.id, phaseSel, groupeSel || null);
      setMatch(m);
      setMsg("Phase et groupe enregistrés.");
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function load() {
    try {
      const [m, e, p] = await Promise.all([
        collecteur ? api.match(id) : api.matchGestion(id),
        api.evenementsStaff(id),
        api.participations(id).catch(() => []),
      ]);
      setMatch(m);
      setEvts(e || []);
      setParts(p || []);
      const [jd, je] = await Promise.all([
        api.joueurs(m.equipe_domicile_id).catch(() => []),
        api.joueurs(m.equipe_exterieur_id).catch(() => []),
      ]);
      setJoueursDom(jd || []);
      setJoueursExt(je || []);
      const draft = {};
      (p || []).forEach((x) => {
        draft[x.joueur_id] = x.statut;
      });
      setCompDraft(draft);
    } catch (ex) {
      setErr(ex.message);
      if (ex.status === 401) {
        clearTokens();
        nav("/login", { replace: true });
      }
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!running) return undefined;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [running]);

  const liveMin = useMemo(() => {
    if (!match?.started_at) return 0;
    return clockFromMatch(match, now).min;
  }, [match, now]);

  useEffect(() => {
    if (running) setMinute(String(liveMin));
  }, [running, liveMin]);

  async function act(fn, ok) {
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      await fn();
      setMsg(ok);
      await load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  function demarrer() {
    return act(() => api.changerStatut(id, "en_cours"), "Coup d’envoi. 1re période.");
  }
  function miTemps() {
    return act(() => api.changerPeriode(id, "mi_temps"), "Mi-temps. Chrono arrêté.");
  }
  function reprise() {
    return act(() => api.changerPeriode(id, "2"), "2e période. Le chrono reprend à 45′.");
  }
  function terminer() {
    return act(() => api.changerStatut(id, "termine"), "Match terminé. Chrono figé.");
  }
  function publier() {
    return act(() => api.validerMatch(id), "Match validé. Classement officiel à jour.");
  }
  function contester() {
    return act(() => api.changerStatut(id, "conteste"), "Match contesté. Hors classement.");
  }
  function forfait(equipe) {
    const nom = equipe === "domicile" ? home : away;
    return act(() => api.forfait(id, equipe), `Forfait ${nom} : 0–3. À valider pour le classement.`);
  }

  async function enregistrerFeuille() {
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const deja = new Set(parts.map((p) => p.joueur_id));
      const lignes = [];
      const pushClub = (liste, equipe, clubId) => {
        liste.forEach((j) => {
          const st = compDraft[j.id];
          if (!st || deja.has(j.id)) return;
          lignes.push({
            joueur_id: j.id,
            club_id: clubId,
            equipe_concernee: equipe,
            statut: st,
            minute_entree: st === "titulaire" ? 0 : 0,
          });
        });
      };
      pushClub(joueursDom, "domicile", match.equipe_domicile_id);
      pushClub(joueursExt, "exterieur", match.equipe_exterieur_id);
      for (const payload of lignes) {
        await api.ajouterParticipation(id, payload);
      }
      setMsg(lignes.length ? "Feuille enregistrée." : "Rien de nouveau à enregistrer.");
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  function nomJoueur(jid) {
    const j = [...joueursDom, ...joueursExt].find((x) => x.id === jid);
    return j?.nom_complet || "Joueur";
  }

  function estExpulse(jid) {
    return evts.some(
      (e) =>
        e.joueur_id === jid
        && e.type === "carton_rouge"
        && e.statut_validation === "valide"
        && !e.refuse,
    );
  }

  async function ajouter(e) {
    e.preventDefault();
    if (!joueurId) {
      setErr("Choisissez un joueur.");
      return;
    }
    if ((type === "remplacement") && !secondaireId) {
      setErr("Indiquez le joueur qui entre.");
      return;
    }
    if (estExpulse(Number(joueurId)) || (secondaireId && estExpulse(Number(secondaireId)))) {
      setErr("Ce joueur est déjà expulsé.");
      return;
    }
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const split = splitMinute(minute, periode === "2" ? "2" : "1");
      const payload = {
        temp_id: crypto.randomUUID(),
        minute: split.minute,
        minute_additionnelle: split.minute_additionnelle,
        periode: split.periode,
        type,
        joueur_id: Number(joueurId),
        equipe_concernee: cote,
      };
      if (type === "but" && secondaireId) payload.joueur_secondaire_id = Number(secondaireId);
      if (type === "remplacement") payload.joueur_secondaire_id = Number(secondaireId);
      if (type === "penalty") payload.resultat = resultat;
      const cree = await api.saisirEvenement(id, payload);
      if (cree?.statut_validation === "en_attente") {
        setMsg(`${LABELS[type] || type} enregistré — en attente de validation.`);
      } else {
        setMsg(`${LABELS[type] || type} enregistré.`);
      }
      setSecondaireId("");
      await load();
    } catch (ex) {
      setErr(ex.message);
      await load();
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  function cycleComp(joueurId) {
    setCompDraft((d) => {
      const cur = d[joueurId];
      const next = cur === "titulaire" ? "remplacant" : cur === "remplacant" ? "" : "titulaire";
      const copy = { ...d };
      if (!next) delete copy[joueurId];
      else copy[joueurId] = next;
      return copy;
    });
  }

  function peutValiderFait(e) {
    return !collecteur && !match.locked && e.statut_validation === "en_attente";
  }

  function validerFait(e) {
    return act(() => api.validerEvenement(e.id), "Fait validé.");
  }

  function rejeterFait(e) {
    const c = rejetCommentaire.trim();
    if (!c) {
      setErr("Indiquez un motif de rejet.");
      return;
    }
    setRejetId(null);
    return act(() => api.rejeterEvenement(e.id, c), "Fait rejeté. Pas au public.");
  }

  function peutRefuser(e) {
    return (
      !collecteur
      && !match.locked
      && e.statut_validation === "valide"
      && !e.refuse
      && ["but", "but_contre_son_camp", "penalty"].includes(e.type)
    );
  }

  function refuser(e) {
    return act(
      () => api.refuserArbitral(e.id, refusMotif),
      "Fait refusé. Score et stats inversés. L'événement reste en feuille.",
    );
  }

  function badgeComp(joueurId) {
    const st = compDraft[joueurId];
    if (st === "titulaire") return "Titu";
    if (st === "remplacant") return "Banc";
    return "—";
  }

  if (!match) return <p className="empty">Chargement…</p>;

  const formOk = enCours && !ht && !match.locked;
  const feuille = grouperFaits(evts);
  const nAttente = evts.filter((e) => e.statut_validation === "en_attente").length;

  return (
    <>
      <p className="kicker" style={{ paddingTop: "0.4rem" }}>
        <Link to={backTo}>← Matchs</Link>
      </p>
      <section className="hero">
        <p className="kicker">
          {match.journee} · {STATUT_MATCH[match.statut] || match.statut}
          {periodeLabel(periode) ? ` · ${periodeLabel(periode)}` : ""}
        </p>
        <h1>{home} {match.score_domicile}–{match.score_exterieur} {away}</h1>
        {enCours && (
          <p className="live-now" style={{ marginTop: "0.6rem" }}>
            <span className="live-dot" aria-hidden="true"><b /></span>
            {ht ? "Mi-temps" : "En cours"}
          </p>
        )}
        {(enCours || match.statut === "termine") && match.started_at && (
          <Chrono match={match} running={running} endedAt={match.ended_at} />
        )}
      </section>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}

      <div className="orga-actions">
        {match.statut === "programme" && (
          <button className="btn btn-primary" type="button" disabled={busy} onClick={demarrer}>
            Démarrer — coup d’envoi
          </button>
        )}
        {enCours && periode !== "mi_temps" && periode !== "2" && (
          <button className="btn" type="button" disabled={busy} onClick={miTemps}>
            Mi-temps
          </button>
        )}
        {ht && (
          <button className="btn btn-primary" type="button" disabled={busy} onClick={reprise}>
            Reprise — 2e période
          </button>
        )}
        {enCours && (
          <button className="btn" type="button" disabled={busy} onClick={terminer}>
            Terminer le match
          </button>
        )}
        {match.statut === "termine" && !match.locked && !collecteur && (
          <>
            <button className="btn btn-primary" type="button" disabled={busy || nAttente > 0} onClick={publier}>
              Valider le match
            </button>
            {nAttente > 0 && (
              <p className="empty">D’abord valider ou rejeter les faits en attente ({nAttente}).</p>
            )}
          </>
        )}
        {collecteur && match.statut === "termine" && !match.locked && (
          <p className="empty">Match sifflé. L’organisateur valide pour le classement.</p>
        )}
        {match.locked && <p className="empty">Match verrouillé — plus aucune modification.</p>}
        {!collecteur && match.locked && match.resultat_retroactif && (
          <button className="btn btn-danger" type="button" disabled={busy} onClick={annulerResultatRetroactif}>
            Révoquer le résultat rétroactif et reprogrammer
          </button>
        )}
      </div>

      {!collecteur && !match.locked && match.statut === "programme" && (
        <form className="phase-box" onSubmit={enregistrerResultatRetroactif}>
          <p className="kicker">Correction exceptionnelle</p>
          <p className="lead">
            À utiliser uniquement lorsqu’un match a réellement été joué sans suivre le flux live.
            Cette action valide le score sans inventer de buteurs ni de minutes.
          </p>
          <div className="comp-grid">
            <label className="field">
              Score {home}
              <input type="number" min="0" max="99" value={retroScoreDom} onChange={(e) => setRetroScoreDom(e.target.value)} required />
            </label>
            <label className="field">
              Score {away}
              <input type="number" min="0" max="99" value={retroScoreExt} onChange={(e) => setRetroScoreExt(e.target.value)} required />
            </label>
          </div>
          <label className="field">
            Motif interne de la correction
            <textarea value={retroMotif} onChange={(e) => setRetroMotif(e.target.value)} minLength="10" maxLength="500" required placeholder="Expliquez pourquoi le match est saisi après coup." />
          </label>
          <label className="field">
            Note visible par le public
            <textarea value={retroNote} onChange={(e) => setRetroNote(e.target.value)} minLength="10" maxLength="2000" required />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "…" : "Enregistrer le résultat rétrospectif"}
          </button>
        </form>
      )}

      {!collecteur && !match.locked && match.statut === "programme" && (
        <form className="phase-box" onSubmit={enregistrerProgrammation}>
          <p className="kicker">Programmation</p>
          <div className="comp-grid">
            <label className="field">
              Date
              <input type="date" value={dateProg} onChange={(e) => setDateProg(e.target.value)} required />
            </label>
            <label className="field">
              Heure locale
              <input type="time" value={heureProg} onChange={(e) => setHeureProg(e.target.value)} required />
            </label>
          </div>
          <label className="field">
            Stade
            <input value={stadeProg} onChange={(e) => setStadeProg(e.target.value)} placeholder="à compléter" />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "…" : "Enregistrer la programmation"}
          </button>
        </form>
      )}

      {!collecteur && !match.locked && (
        <div className="phase-box">
          <p className="kicker">Phase & groupe</p>
          <div className="phase-row">
            <label className="field">
              Phase
              <select value={phaseSel} onChange={(e) => setPhaseSel(e.target.value)}>
                <option value="poule">Poule</option>
                <option value="quart">Quart de finale</option>
                <option value="demi">Demi-finale</option>
                <option value="finale">Finale</option>
              </select>
            </label>
            <label className="field">
              Groupe
              <select value={groupeSel} onChange={(e) => setGroupeSel(e.target.value)}>
                <option value="">Sans groupe</option>
                <option value="A">A</option>
                <option value="B">B</option>
                <option value="C">C</option>
                <option value="D">D</option>
              </select>
            </label>
            <button className="btn" type="button" disabled={busy} onClick={enregistrerPhase}>
              Enregistrer
            </button>
          </div>
        </div>
      )}

      {!collecteur && match.resultat_retroactif && match.locked && match.buteurs_a_verifier && (
        <form className="phase-box" onSubmit={enregistrerButeursVerifies}>
          <p className="kicker">Buteurs vérifiés</p>
          <p className="lead">
            Les buteurs sont enregistrés chez les organisateurs. Après vérification, renseignez-les ici.
            Le score officiel ne sera pas recalculé.
          </p>
          {buteursRetro.map((buteur, index) => {
            const liste = buteur.equipe_concernee === "exterieur" ? joueursExt : joueursDom;
            return (
              <div className="comp-grid" key={`${buteur.equipe_concernee}-${index}`}>
                <label className="field">
                  Équipe du buteur {index + 1}
                  <select value={buteur.equipe_concernee} onChange={(e) => modifierButeur(index, "equipe_concernee", e.target.value)}>
                    <option value="domicile">{home}</option>
                    <option value="exterieur">{away}</option>
                  </select>
                </label>
                <label className="field">
                  Joueur
                  <select value={buteur.joueur_id} onChange={(e) => modifierButeur(index, "joueur_id", e.target.value)} required>
                    <option value="">—</option>
                    {liste.map((joueur) => <option key={joueur.id} value={joueur.id}>{joueur.nom_complet}</option>)}
                  </select>
                </label>
                <label className="field">
                  Minute connue (facultatif)
                  <input type="number" min="0" max="130" value={buteur.minute} onChange={(e) => modifierButeur(index, "minute", e.target.value)} placeholder="non précisée" />
                </label>
              </div>
            );
          })}
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "…" : "Ajouter les buteurs vérifiés"}
          </button>
        </form>
      )}

      {formOk && (
        <form className="compte-form" onSubmit={ajouter} style={{ marginTop: "0.4rem" }}>
          <p className="kicker">Fait de jeu</p>
          <div className="type-row" role="group" aria-label="Type">
            {TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                className={type === t.value ? "on" : ""}
                onClick={() => {
                  setType(t.value);
                  setSecondaireId("");
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
          {TYPE_SENS[type] && (
            <p className="empty" style={{ paddingTop: 0 }}>{TYPE_SENS[type]}</p>
          )}
          <label className="field">
            Équipe
            <select value={cote} onChange={(e) => { setCote(e.target.value); setJoueurId(""); setSecondaireId(""); }}>
              <option value="domicile">{home}</option>
              <option value="exterieur">{away}</option>
            </select>
          </label>
          <label className="field">
            {type === "remplacement" ? "Sortant" : type === "but_contre_son_camp" ? "Joueur fautif" : "Joueur"}
            <select value={joueurId} onChange={(e) => setJoueurId(e.target.value)} required>
              <option value="">—</option>
              {joueurs.map((j) => (
                <option key={j.id} value={j.id} disabled={estExpulse(j.id)}>
                  {j.nom_complet}{estExpulse(j.id) ? " — expulsé" : ""}
                </option>
              ))}
            </select>
          </label>
          {type === "but" && (
            <label className="field">
              Passeur (optionnel)
              <select value={secondaireId} onChange={(e) => setSecondaireId(e.target.value)}>
                <option value="">Aucune passe décisive</option>
                {joueurs.filter((j) => String(j.id) !== String(joueurId)).map((j) => (
                  <option key={j.id} value={j.id} disabled={estExpulse(j.id)}>
                    {j.nom_complet}{estExpulse(j.id) ? " — expulsé" : ""}
                  </option>
                ))}
              </select>
            </label>
          )}
          {type === "remplacement" && (
            <label className="field">
              Entrant
              <select value={secondaireId} onChange={(e) => setSecondaireId(e.target.value)} required>
                <option value="">—</option>
                {joueurs.filter((j) => String(j.id) !== String(joueurId)).map((j) => (
                  <option key={j.id} value={j.id} disabled={estExpulse(j.id)}>
                    {j.nom_complet}{estExpulse(j.id) ? " — expulsé" : ""}
                  </option>
                ))}
              </select>
            </label>
          )}
          {type === "penalty" && (
            <label className="field">
              Tir
              <select value={resultat} onChange={(e) => setResultat(e.target.value)}>
                <option value="marque">Marqué</option>
                <option value="rate">Raté</option>
              </select>
            </label>
          )}
          <label className="field">
            Minute
            <input
              type="number"
              min="0"
              max="130"
              step="1"
              value={minute}
              onChange={(e) => setMinute(e.target.value)}
              required
            />
          </label>
          <p className="kicker">
            Enregistré comme {formatMinute(splitMinute(minute, periode === "2" ? "2" : "1").minute, splitMinute(minute, periode === "2" ? "2" : "1").minute_additionnelle)}
            {periode === "2" ? " · 2e période" : " · 1re période"}
          </p>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            Enregistrer
          </button>
        </form>
      )}

      {ht && <p className="empty">Mi-temps. Pas de saisie avant la reprise.</p>}

      <div className="section-head">
        <h2>Feuille</h2>
      </div>
      {evts.length === 0 && <p className="empty">Aucun événement.</p>}
      <ul className="timeline">
        {feuille.map((e) => (
          <li key={e.id}>
            {(e.minute_connue === false ? "Minute non précisée" : formatMinute(e.minute, e.minute_additionnelle))} · {labelEvenement(e)}
            {e.type === "remplacement"
              ? ` · Sort : ${nomJoueur(e.joueur_id)} → Entre : ${nomJoueur(e.joueur_secondaire_id)}`
              : e.type === "passe_decisive"
                ? ` · ${nomJoueur(e.joueur_secondaire_id)} pour ${nomJoueur(e.joueur_id)}`
                : ` · ${nomJoueur(e.joueur_id)}`}
            {e.joueur_secondaire_id && e.type === "but" ? ` · Passe décisive ${nomJoueur(e.joueur_secondaire_id)}` : ""}
            {e.refuse ? ` · refusé (${MOTIF_REFUS[e.motif_refus] || e.motif_refus})` : ` · ${STATUT_FAIT[e.statut_validation] || e.statut_validation}`}
            {peutValiderFait(e) && (
              <div className="file-actions">
                <button className="btn btn-primary" type="button" disabled={busy} onClick={() => validerFait(e)}>
                  Valider
                </button>
                {rejetId === e.id ? (
                  <>
                    <input
                      className="field-inline"
                      value={rejetCommentaire}
                      onChange={(ev) => setRejetCommentaire(ev.target.value)}
                      placeholder="Motif du rejet"
                    />
                    <button className="btn btn-danger" type="button" disabled={busy} onClick={() => rejeterFait(e)}>
                      Confirmer le rejet
                    </button>
                  </>
                ) : (
                  <button
                    className="btn btn-danger"
                    type="button"
                    disabled={busy}
                    onClick={() => { setRejetId(e.id); setRejetCommentaire(""); }}
                  >
                    Rejeter
                  </button>
                )}
              </div>
            )}
            {peutRefuser(e) && (
              <div className="file-actions">
                {refusId === e.id ? (
                  <>
                    <select
                      className="field-inline"
                      value={refusMotif}
                      onChange={(ev) => setRefusMotif(ev.target.value)}
                    >
                      {Object.entries(MOTIF_REFUS).map(([k, lab]) => (
                        <option key={k} value={k}>{lab}</option>
                      ))}
                    </select>
                    <button className="btn btn-danger" type="button" disabled={busy} onClick={() => { setRefusId(null); refuser(e); }}>
                      Confirmer le refus
                    </button>
                  </>
                ) : (
                  <button className="btn btn-danger" type="button" disabled={busy} onClick={() => setRefusId(e.id)}>
                    Refuser
                  </button>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>

      {!collecteur && !match.locked && match.statut !== "valide" && (
        <>
          <div className="section-head">
            <h2>Compositions</h2>
          </div>
          <p className="lead">Toucher un nom : titulaire, banc, ou rien. Quatre joueurs DEMO suffisent pour tester un changement.</p>
          <div className="comp-grid">
            <div>
              <p className="kicker">{home}</p>
              {joueursDom.map((j) => (
                <button key={j.id} type="button" className="comp-row" onClick={() => cycleComp(j.id)}>
                  <span>{j.nom_complet}</span>
                  <strong>{badgeComp(j.id)}</strong>
                </button>
              ))}
            </div>
            <div>
              <p className="kicker">{away}</p>
              {joueursExt.map((j) => (
                <button key={j.id} type="button" className="comp-row" onClick={() => cycleComp(j.id)}>
                  <span>{j.nom_complet}</span>
                  <strong>{badgeComp(j.id)}</strong>
                </button>
              ))}
            </div>
          </div>
          <button className="btn" type="button" disabled={busy} onClick={enregistrerFeuille} style={{ marginTop: "0.7rem" }}>
            Enregistrer la feuille
          </button>
        </>
      )}

      {!collecteur && !match.locked && match.statut !== "valide" && (
        <>
          <p className="kicker" style={{ marginTop: "1.6rem" }}>
            <button className="linkish" type="button" onClick={() => setAutre((v) => !v)}>
              {autre ? "Masquer" : "Forfait / contestation"}
            </button>
          </p>
          {autre && (
            <div className="orga-actions">
              {match.statut !== "conteste" && (
                <button className="btn" type="button" disabled={busy} onClick={contester}>Contester le match</button>
              )}
              {match.statut !== "termine" && (
                <>
                  <button className="btn btn-danger" type="button" disabled={busy} onClick={() => forfait("domicile")}>
                    Forfait {home} (0–3)
                  </button>
                  <button className="btn btn-danger" type="button" disabled={busy} onClick={() => forfait("exterieur")}>
                    Forfait {away} (0–3)
                  </button>
                </>
              )}
            </div>
          )}
        </>
      )}
    </>
  );
}
