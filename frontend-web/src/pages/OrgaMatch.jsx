import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, clearTokens } from "../api.js";
import Chrono from "../components/Chrono.jsx";
import { clubName, useKivu } from "../context.jsx";
import { clockFromMatch, formatMinute, MOTIF_REFUS, periodeLabel, splitMinute, stripDemo } from "../display.js";

const LABELS = {
  but: "But",
  carton_jaune: "Jaune",
  carton_rouge: "Rouge",
  but_contre_son_camp: "CSC",
  penalty: "Penalty",
  remplacement: "Changement",
  passe_decisive: "Passe",
};

const TYPES = [
  { value: "but", label: "But" },
  { value: "but_contre_son_camp", label: "CSC" },
  { value: "penalty", label: "Penalty" },
  { value: "carton_jaune", label: "Jaune" },
  { value: "carton_rouge", label: "Rouge" },
  { value: "remplacement", label: "Changement" },
];

export default function OrgaMatch() {
  const { id } = useParams();
  const nav = useNavigate();
  const { clubsById } = useKivu();
  const [match, setMatch] = useState(null);
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
  const [minute, setMinute] = useState("0");
  const [now, setNow] = useState(Date.now());
  const [compDraft, setCompDraft] = useState({});
  const [autre, setAutre] = useState(false);
  const [refusId, setRefusId] = useState(null);
  const [refusMotif, setRefusMotif] = useState("hors_jeu");

  const home = stripDemo(clubName(clubsById, match?.equipe_domicile_id));
  const away = stripDemo(clubName(clubsById, match?.equipe_exterieur_id));
  const joueurs = cote === "exterieur" ? joueursExt : joueursDom;
  const periode = match?.periode || (match?.statut === "en_cours" ? "1" : null);
  const enCours = match?.statut === "en_cours";
  const ht = enCours && periode === "mi_temps";
  const running = enCours && !ht;

  async function load() {
    try {
      const [m, e, p] = await Promise.all([
        api.matchGestion(id),
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
      await api.saisirEvenement(id, payload);
      setMsg(`${LABELS[type] || type} enregistré.`);
      setSecondaireId("");
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
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

  function peutRefuser(e) {
    return (
      !match.locked
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

  return (
    <div className="shell">
      <p className="kicker" style={{ paddingTop: "1rem" }}>
        <Link to="/orga">← Organisateur</Link>
      </p>
      <section className="hero">
        <p className="kicker">
          {match.journee} · {match.statut}
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
        {match.statut === "termine" && !match.locked && (
          <button className="btn btn-primary" type="button" disabled={busy} onClick={publier}>
            Valider le match
          </button>
        )}
        {match.locked && <p className="empty">Match verrouillé — plus aucune modification.</p>}
      </div>

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
                <option key={j.id} value={j.id}>{j.nom_complet}</option>
              ))}
            </select>
          </label>
          {type === "but" && (
            <label className="field">
              Passeur (optionnel)
              <select value={secondaireId} onChange={(e) => setSecondaireId(e.target.value)}>
                <option value="">Aucune passe décisive</option>
                {joueurs.filter((j) => String(j.id) !== String(joueurId)).map((j) => (
                  <option key={j.id} value={j.id}>{j.nom_complet}</option>
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
                  <option key={j.id} value={j.id}>{j.nom_complet}</option>
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
          {type === "but_contre_son_camp" && (
            <p className="empty" style={{ paddingTop: 0 }}>Le but est crédité à l’adversaire. Pas au joueur.</p>
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
        {evts.map((e) => (
          <li key={e.id}>
            {formatMinute(e.minute, e.minute_additionnelle)} · {LABELS[e.type] || e.type}
            {e.type === "penalty" && e.resultat ? ` ${e.resultat}` : ""}
            {e.type === "remplacement"
              ? ` · OUT ${nomJoueur(e.joueur_id)} · IN ${nomJoueur(e.joueur_secondaire_id)}`
              : e.type === "passe_decisive"
                ? ` · ${nomJoueur(e.joueur_secondaire_id)} pour ${nomJoueur(e.joueur_id)}`
                : ` · ${nomJoueur(e.joueur_id)}`}
            {e.joueur_secondaire_id && e.type === "but" ? ` · passe ${nomJoueur(e.joueur_secondaire_id)}` : ""}
            {e.refuse ? ` · refusé (${MOTIF_REFUS[e.motif_refus] || e.motif_refus})` : ` · ${e.statut_validation}`}
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

      {!match.locked && match.statut !== "valide" && (
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

      {!match.locked && match.statut !== "valide" && (
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
    </div>
  );
}
