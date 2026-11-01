import { useState } from "react";
import { api } from "../api.js";
import { PHASES_ELIMINATOIRES, scoreTirsAuBut, vainqueurTirsAuBut } from "../tirsAuBut.js";

function nomEquipe(tir, home, away) {
  return tir.equipe_concernee === "exterieur" ? away : home;
}

function nomJoueur(tir, joueurs = {}) {
  return tir.joueur_id ? joueurs[tir.joueur_id]?.nom_complet || "Joueur à compléter" : "Tireur non précisé";
}

function SequenceTirs({ tirs, home, away, joueurs = {} }) {
  return (
    <div className="tirs-sequence" aria-label="Résultat tir par tir">
      {[
        { cote: "domicile", nom: home },
        { cote: "exterieur", nom: away },
      ].map(({ cote, nom }) => {
        const essais = tirs.filter((tir) => tir.equipe_concernee === cote);
        return (
          <div className="tirs-sequence-row" key={cote}>
            <span className="tirs-sequence-team" title={nom}>{nom}</span>
            <div className="tirs-sequence-pills">
              {essais.length === 0 ? <span className="tirs-sequence-empty">—</span> : essais.map((tir) => {
                const marque = tir.resultat === "marque";
                const resultat = marque ? "réussi" : "raté ou arrêté";
                const titre = `Tir ${tir.ordre} · ${nomJoueur(tir, joueurs)} · ${resultat}`;
                return (
                  <span
                    className={`tirs-pill${marque ? " is-marque" : " is-rate"}`}
                    key={tir.ordre}
                    role="img"
                    title={titre}
                    aria-label={titre}
                  >
                    {marque ? "✓" : "✗"}
                  </span>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function HistoriqueTirs({ tirs, home, away, joueurs = {}, editable = false, onAnnuler }) {
  if (tirs.length === 0) return <p className="empty">Aucun tir enregistré.</p>;
  return (
    <ol className="timeline tirs-historique">
      {tirs.map((tir) => (
        <li key={tir.ordre}>
          #{tir.ordre} · {nomEquipe(tir, home, away)} · {nomJoueur(tir, joueurs)} · {tir.resultat === "marque" ? "Marqué" : "Raté / arrêté"}
          {editable && tir.ordre === tirs[tirs.length - 1]?.ordre && (
            <button className="btn btn-danger" type="button" onClick={onAnnuler}>Annuler le dernier tir</button>
          )}
        </li>
      ))}
    </ol>
  );
}

function ListeTirsAdmin({ tirs, home, away, joueurs, editable, onAnnuler }) {
  const score = scoreTirsAuBut(tirs);
  const vainqueur = vainqueurTirsAuBut(tirs);
  return (
    <>
      <div className="section-head">
        <h2>Séance de tirs au but</h2>
        <span className="stamp">{score.domicile}–{score.exterieur}</span>
      </div>
      <p className="muted small">Séance séparée du score du match : les tirs ne modifient ni les buts ni les statistiques ordinaires.</p>
      <SequenceTirs tirs={tirs} home={home} away={away} joueurs={joueurs} />
      {vainqueur && <p className="empty">Vainqueur de la séance : {vainqueur === "domicile" ? home : away}.</p>}
      <HistoriqueTirs tirs={tirs} home={home} away={away} joueurs={joueurs} editable={editable} onAnnuler={onAnnuler} />
    </>
  );
}

export function TirsAuButPublic({ match, home, away, joueurs = {} }) {
  const tirs = Array.isArray(match?.tirs_au_but) ? match.tirs_au_but : [];
  if (!tirs.length) return null;
  const score = scoreTirsAuBut(tirs);
  const vainqueur = vainqueurTirsAuBut(tirs);

  return (
    <section className="sheet tirs-au-but">
      <details className="tirs-public-details">
        <summary className="tirs-public-summary">
          <span className="tirs-public-title">Séance de tirs au but</span>
          <span className="tirs-public-score">{score.domicile}–{score.exterieur}<span className="tirs-public-chevron" aria-hidden="true">⌄</span></span>
        </summary>
        <div className="tirs-public-body">
          <p className="muted small">Résultat distinct du score du match. Les tirs ne modifient ni les buts ni le classement des poules.</p>
          <SequenceTirs tirs={tirs} home={home} away={away} joueurs={joueurs} />
          {vainqueur && <p className="tirs-public-winner">Vainqueur de la séance · <strong>{vainqueur === "domicile" ? home : away}</strong></p>}
          <details className="tirs-historique-details">
            <summary>Voir le détail des tireurs</summary>
            <HistoriqueTirs tirs={tirs} home={home} away={away} joueurs={joueurs} />
          </details>
        </div>
      </details>
    </section>
  );
}

export function TirsAuButAdmin({ match, home, away, joueursDom = [], joueursExt = [], onUpdated }) {
  const tirs = Array.isArray(match?.tirs_au_but) ? match.tirs_au_but : [];
  const isKnockout = PHASES_ELIMINATOIRES.includes(match?.phase);
  const scoreHome = Number(match?.score_domicile);
  const scoreAway = Number(match?.score_exterieur);
  const egalite = match?.score_domicile != null
    && match?.score_exterieur != null
    && Number.isFinite(scoreHome)
    && Number.isFinite(scoreAway)
    && scoreHome === scoreAway;
  const matchTermine = ["termine", "valide"].includes(match?.statut);
  const editable = isKnockout && egalite && match?.statut === "termine" && !match?.locked && !match?.forfait;
  const [equipe, setEquipe] = useState("domicile");
  const [joueurId, setJoueurId] = useState("");
  const [busy, setBusy] = useState(false);
  const [erreur, setErreur] = useState("");
  const [message, setMessage] = useState("");

  if (!isKnockout || (!matchTermine && !tirs.length)) return null;

  const equipeASaisir = tirs.length
    ? (tirs[tirs.length - 1].equipe_concernee === "domicile" ? "exterieur" : "domicile")
    : equipe;
  const listeJoueurs = equipeASaisir === "exterieur" ? joueursExt : joueursDom;
  const prochainVainqueur = vainqueurTirsAuBut(tirs);
  const equipesJoueurs = Object.fromEntries([...joueursDom, ...joueursExt].map((joueur) => [joueur.id, joueur]));
  const nomEquipeASaisir = equipeASaisir === "exterieur" ? away : home;

  async function enregistrer(resultatTir) {
    if (busy || !joueurId) return;
    setBusy(true);
    setErreur("");
    setMessage("");
    try {
      const updated = await api.ajouterTirAuBut(match.id, {
        equipe_concernee: equipeASaisir,
        joueur_id: Number(joueurId),
        resultat: resultatTir,
      });
      onUpdated?.(updated);
      setJoueurId("");
      setMessage(`Tir ${resultatTir === "marque" ? "marqué" : "raté / arrêté"} enregistré. Le score normal du match reste inchangé.`);
    } catch (error) {
      setErreur(error.message || "Impossible d’enregistrer ce tir.");
    } finally {
      setBusy(false);
    }
  }

  async function annulerDernier() {
    if (!window.confirm("Retirer le dernier tir de la séance ? Le score normal du match ne changera pas.")) return;
    setBusy(true);
    setErreur("");
    setMessage("");
    try {
      const prochainCote = tirs[tirs.length - 1]?.equipe_concernee;
      const updated = await api.annulerDernierTirAuBut(match.id);
      onUpdated?.(updated);
      if (prochainCote) setEquipe(prochainCote);
      setMessage("Dernier tir retiré.");
    } catch (error) {
      setErreur(error.message || "Impossible de retirer le dernier tir.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="sheet tirs-au-but">
      <ListeTirsAdmin
        tirs={tirs}
        home={home}
        away={away}
        joueurs={equipesJoueurs}
        editable={editable && !busy}
        onAnnuler={annulerDernier}
      />
      {editable && !prochainVainqueur ? (
        <div className="tirs-saisie">
          <div className="tirs-saisie-head">
            <p className="kicker">Saisie organisateur</p>
            {tirs.length === 0 ? (
              <label className="field">
                Équipe qui commence
                <select value={equipe} onChange={(event) => { setEquipe(event.target.value); setJoueurId(""); }} disabled={busy}>
                  <option value="domicile">{home}</option>
                  <option value="exterieur">{away}</option>
                </select>
              </label>
            ) : (
              <p className="tirs-prochain">Prochain tir · <strong>{nomEquipeASaisir}</strong></p>
            )}
          </div>
          <label className="field">
            Tireur
            <select value={joueurId} onChange={(event) => setJoueurId(event.target.value)} disabled={busy}>
              <option value="">Choisir un joueur</option>
              {listeJoueurs.map((joueur) => <option key={joueur.id} value={joueur.id}>{joueur.nom_complet}</option>)}
            </select>
          </label>
          <p className="muted small">Choisissez le tireur, puis touchez ✓ ou ✗. L’équipe suivante est calculée automatiquement et la séance s’arrête dès qu’un vainqueur est certain.</p>
          <div className="tirs-actions" role="group" aria-label="Résultat du tir">
            <button className="btn tirs-action tirs-action-marque" type="button" disabled={busy || !joueurId} onClick={() => enregistrer("marque")}>
              {busy ? "Enregistrement…" : "✓ Marqué"}
            </button>
            <button className="btn tirs-action tirs-action-rate" type="button" disabled={busy || !joueurId} onClick={() => enregistrer("rate")}>
              {busy ? "Enregistrement…" : "✗ Raté / arrêté"}
            </button>
          </div>
        </div>
      ) : editable && prochainVainqueur ? (
        <p className="empty">Séance décidée : {prochainVainqueur === "domicile" ? home : away} l’emporte. Validez le résultat du match pour confirmer la qualification.</p>
      ) : !egalite ? (
        <p className="empty">Match terminé sans égalité : aucune séance de tirs au but à saisir.</p>
      ) : (
        <p className="empty">Séance en lecture seule.</p>
      )}
      {erreur && <p className="erreur" role="alert">{erreur}</p>}
      {message && <p className="empty" role="status">{message}</p>}
    </section>
  );
}
