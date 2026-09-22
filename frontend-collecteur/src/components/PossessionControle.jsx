import { useEffect, useMemo, useState } from "react";
import { fetchPossessionGestion, transitionPossession } from "../lib/api";

const TEAM_A = "TEAM_A";
const TEAM_B = "TEAM_B";
const PAUSE = "PAUSE";
const FINISHED = "FINISHED";

function uuid() {
  return typeof crypto?.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function duree(ms) {
  const total = Math.max(0, Math.floor((Number(ms) || 0) / 1000));
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

export default function PossessionControle({ matchId, match, onMatchReload }) {
  const [possession, setPossession] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(Date.now());

  async function load() {
    try {
      setPossession(await fetchPossessionGestion(matchId));
    } catch (e) {
      setError(e.message || "Possession indisponible.");
    }
  }

  useEffect(() => {
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matchId]);

  useEffect(() => {
    if (!possession?.intervalle_ouvert_depuis || possession.etat_courant === FINISHED) return undefined;
    const timer = setInterval(() => setTick(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [possession?.intervalle_ouvert_depuis, possession?.etat_courant]);

  const compteurs = useMemo(() => {
    const valeurs = {
      a: Number(possession?.temps_a_ms || 0),
      b: Number(possession?.temps_b_ms || 0),
      pause: Number(possession?.temps_non_attribue_ms || 0),
    };
    if (possession?.intervalle_ouvert_depuis && possession.etat_courant !== FINISHED) {
      const delta = Math.max(0, tick - new Date(possession.intervalle_ouvert_depuis).getTime());
      if (possession.etat_courant === TEAM_A) valeurs.a += delta;
      if (possession.etat_courant === TEAM_B) valeurs.b += delta;
      if (possession.etat_courant === PAUSE) valeurs.pause += delta;
    }
    return valeurs;
  }, [possession, tick]);

  async function action(etat) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const suivant = await transitionPossession(matchId, etat, uuid());
      setPossession(suivant);
      onMatchReload?.();
    } catch (e) {
      setError(e.message || "Commande non enregistrée. La connexion est nécessaire pour le chronomètre.");
    } finally {
      setBusy(false);
    }
  }

  const etat = possession?.etat_courant || "NOT_STARTED";
  const termine = etat === FINISHED;
  const miTemps = match?.periode === "mi_temps";
  const enCours = match?.statut === "en_cours";
  const repriseDisponible = etat === PAUSE && match?.periode === "2" && enCours;

  return (
    <section className="bloc-possession">
      <div className="possession-titre">
        <div>
          <p className="eyebrow">KIVUFOOT POSSESSION V1</p>
          <h2>Temps de contrôle</h2>
        </div>
        <b className={`possession-etat possession-etat-${etat.toLowerCase()}`}>{etat}</b>
      </div>
      <div className="possession-compteurs">
        <div><span>Domicile</span><strong>{duree(compteurs.a)}</strong></div>
        <div><span>Pause / non attribué</span><strong>{duree(compteurs.pause)}</strong></div>
        <div><span>Extérieur</span><strong>{duree(compteurs.b)}</strong></div>
      </div>
      <p className="possession-note">Une passe entre joueurs ne change rien. Duel, déviation ou doute : PAUSE.</p>
      <div className="possession-actions">
        <button disabled={busy || termine || !enCours || miTemps || repriseDisponible} onClick={() => action(TEAM_A)}>A · DOMICILE</button>
        <button disabled={busy || termine || !enCours || miTemps || repriseDisponible} onClick={() => action(TEAM_B)}>B · EXTÉRIEUR</button>
        <button disabled={busy || termine || etat === "NOT_STARTED"} onClick={() => action(PAUSE)}>PAUSE</button>
        {repriseDisponible && <>
          <button disabled={busy} onClick={() => action(TEAM_A)}>REPRENDRE A</button>
          <button disabled={busy} onClick={() => action(TEAM_B)}>REPRENDRE B</button>
        </>}
        <button className="possession-terminer" disabled={busy || termine || !enCours} onClick={() => action(FINISHED)}>TERMINER</button>
      </div>
      {error && <p className="erreur">{error}</p>}
      <p className="possession-meta">
        {possession?.nombre_sequences_a || 0} séquence(s) A · {possession?.nombre_sequences_b || 0} séquence(s) B · {possession?.nombre_changements || 0} changement(s)
      </p>
    </section>
  );
}
