import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";

const ETATS = {
  TEAM_A: "TEAM_A",
  TEAM_B: "TEAM_B",
  PAUSE: "PAUSE",
  FINISHED: "FINISHED",
};

function secondes(ms) {
  return Math.max(0, Math.floor((Number(ms) || 0) / 1000));
}

function formatDuree(ms) {
  const total = secondes(ms);
  const min = Math.floor(total / 60).toString().padStart(2, "0");
  const sec = (total % 60).toString().padStart(2, "0");
  return `${min}:${sec}`;
}

function uuid() {
  return typeof crypto?.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function PossessionControle({ match, possession, onChange, mode = "collecteur" }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(Date.now());
  const isOrganizer = mode === "organisateur";
  const teamA = possession?.equipe_a_nom || "Domicile";
  const teamB = possession?.equipe_b_nom || "Extérieur";

  useEffect(() => {
    if (!possession?.intervalle_ouvert_depuis || possession.etat_courant === "FINISHED") return undefined;
    const timer = setInterval(() => setTick(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [possession?.intervalle_ouvert_depuis, possession?.etat_courant]);

  const live = useMemo(() => {
    const result = {
      a: Number(possession?.temps_a_ms || 0),
      b: Number(possession?.temps_b_ms || 0),
      pause: Number(possession?.temps_non_attribue_ms || 0),
    };
    if (possession?.intervalle_ouvert_depuis && possession.etat_courant !== "FINISHED") {
      const delta = Math.max(0, tick - new Date(possession.intervalle_ouvert_depuis).getTime());
      if (possession.etat_courant === ETATS.TEAM_A) result.a += delta;
      if (possession.etat_courant === ETATS.TEAM_B) result.b += delta;
      if (possession.etat_courant === ETATS.PAUSE) result.pause += delta;
    }
    return result;
  }, [possession, tick]);

  async function transition(etat, correction = false) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const suivant = await api.transitionPossession(match.id, etat, {
        correction,
        operationId: uuid(),
      });
      onChange?.(suivant);
    } catch (e) {
      setError(e.message || "La commande de possession n'a pas été enregistrée.");
    } finally {
      setBusy(false);
    }
  }

  async function corriger(intervalle) {
    const etatCorrige = window.prompt("État corrigé : TEAM_A, TEAM_B ou PAUSE", intervalle.etat);
    if (!etatCorrige || ![ETATS.TEAM_A, ETATS.TEAM_B, ETATS.PAUSE].includes(etatCorrige)) return;
    const motif = window.prompt("Motif obligatoire de la correction (au moins 10 caractères)", "Correction vérifiée par la chronologie terrain.");
    if (!motif || motif.trim().length < 10) return;
    setBusy(true);
    setError("");
    try {
      const suivant = await api.correctionPossession(match.id, {
        operation_id: uuid(),
        intervalle_id: intervalle.id,
        etat: etatCorrige,
        motif: motif.trim(),
      });
      onChange?.(suivant);
    } catch (e) {
      setError(e.message || "La correction n'a pas été enregistrée.");
    } finally {
      setBusy(false);
    }
  }

  const etat = possession?.etat_courant || "NOT_STARTED";
  const termine = etat === "FINISHED";
  const periode = match?.periode === "mi_temps";
  const repriseDisponible = !termine && etat === "PAUSE" && match?.periode === "2" && match?.statut === "en_cours";
  const peutEquipe = !termine && match?.statut === "en_cours" && !periode && !repriseDisponible;

  return (
    <section className={`sheet possession-controle ${isOrganizer ? "possession-controle-orga" : ""}`}>
      <div className="possession-controle-head">
        <div>
          <p className="kicker">Possession V1 · temps observé</p>
          <h2>{isOrganizer ? "Contrôle et chronologie" : "Chronomètre terrain"}</h2>
        </div>
        <span className={`possession-etat possession-etat-${etat.toLowerCase()}`}>{etat}</span>
      </div>

      <div className="possession-compteurs">
        <div><span>{teamA}</span><strong>{formatDuree(live.a)}</strong></div>
        <div><span>Non attribué</span><strong>{formatDuree(live.pause)}</strong></div>
        <div><span>{teamB}</span><strong>{formatDuree(live.b)}</strong></div>
      </div>

      <p className="muted small">
        A = domicile · B = extérieur. Les passes, tirs et événements ne modifient jamais ce chronomètre.
      </p>

      {!isOrganizer && (
        <div className="possession-actions" aria-label="Commandes possession">
          <button className="possession-action possession-action-a" disabled={busy || !peutEquipe} onClick={() => transition(ETATS.TEAM_A)}>
            A · {teamA}
          </button>
          <button className="possession-action possession-action-b" disabled={busy || !peutEquipe} onClick={() => transition(ETATS.TEAM_B)}>
            B · {teamB}
          </button>
          <button className="possession-action possession-action-pause" disabled={busy || termine || etat === "NOT_STARTED"} onClick={() => transition(ETATS.PAUSE)}>
            PAUSE
          </button>
          {repriseDisponible && (
            <>
              <button className="possession-action possession-action-resume" disabled={busy} onClick={() => transition(ETATS.TEAM_A)}>
                REPRENDRE A
              </button>
              <button className="possession-action possession-action-resume" disabled={busy} onClick={() => transition(ETATS.TEAM_B)}>
                REPRENDRE B
              </button>
            </>
          )}
          <button className="possession-action possession-action-finish" disabled={busy || termine || match?.statut === "programme"} onClick={() => transition(ETATS.FINISHED)}>
            TERMINER
          </button>
        </div>
      )}

      {isOrganizer && (
        <p className="muted small">
          La correction reste auditée et ne supprime aucun intervalle. La validation officielle appartient à l'organisateur du match.
        </p>
      )}

      {error && <p className="erreur possession-error">{error}</p>}
      <div className="possession-mini-meta">
        <span>{possession?.nombre_sequences_a || 0} séquence(s) A</span>
        <span>{possession?.nombre_sequences_b || 0} séquence(s) B</span>
        <span>{possession?.nombre_changements || 0} changement(s)</span>
        <span>{possession?.statut || "PROVISOIRE"}</span>
      </div>

      {isOrganizer && possession?.intervalles?.length > 0 && (
        <details className="possession-chronologie" open>
          <summary>Chronologie détaillée</summary>
          <ol>
            {possession.intervalles.map((intervalle) => (
              <li key={intervalle.id}>
                <strong>{intervalle.etat}</strong>
                <span>{formatDuree(intervalle.duree_ms)}</span>
                <small>{intervalle.debut_at ? new Date(intervalle.debut_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : ""}</small>
                {!intervalle.fin_at ? null : (
                  <button type="button" className="linkish possession-corriger" disabled={busy || possession?.statut === "OFFICIELLE"} onClick={() => corriger(intervalle)}>
                    Corriger
                  </button>
                )}
              </li>
            ))}
          </ol>
        </details>
      )}
    </section>
  );
}
