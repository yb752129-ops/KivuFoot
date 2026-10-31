import { useState } from "react";
import { api } from "../api.js";
import { PHASES_ELIMINATOIRES, scoreTirsAuBut, vainqueurTirsAuBut } from "../tirsAuBut.js";

function nomEquipe(tir, home, away) {
  return tir.equipe_concernee === "exterieur" ? away : home;
}

function nomJoueur(tir, joueurs = {}) {
  return tir.joueur_id ? joueurs[tir.joueur_id]?.nom_complet || "Joueur à compléter" : "Tireur non précisé";
}

function ListeTirs({ tirs, home, away, joueurs, editable = false, onAnnuler }) {
  const score = scoreTirsAuBut(tirs);
  const vainqueur = vainqueurTirsAuBut(tirs);
  return (
    <>
      <div className="section-head">
        <h2>Séance de tirs au but</h2>
        <span className="stamp">{score.domicile}–{score.exterieur}</span>
      </div>
      <p className="muted small">Résultat séparé du score du match. Les tirs ne modifient ni les buts ni les statistiques ordinaires.</p>
      {vainqueur && <p className="empty">Séance décidée : {vainqueur === "domicile" ? home : away} est qualifiée.</p>}
      {tirs.length === 0 ? <p className="empty">Aucun tir enregistré.</p> : (
        <ol className="timeline">
          {tirs.map((tir) => (
            <li key={tir.ordre}>
              #{tir.ordre} · {nomEquipe(tir, home, away)} · {nomJoueur(tir, joueurs)} · {tir.resultat === "marque" ? "Marqué" : "Raté"}
              {editable && tir.ordre === tirs[tirs.length - 1]?.ordre && (
                <button className="btn btn-danger" type="button" onClick={onAnnuler}>Annuler le dernier tir</button>
              )}
            </li>
          ))}
        </ol>
      )}
    </>
  );
}

export function TirsAuButPublic({ match, home, away, joueurs }) {
  const tirs = Array.isArray(match?.tirs_au_but) ? match.tirs_au_but : [];
  if (!tirs.length) return null;
  return <section className="sheet tirs-au-but"><ListeTirs tirs={tirs} home={home} away={away} joueurs={joueurs} /></section>;
}

export function TirsAuButAdmin({ match, home, away, joueursDom = [], joueursExt = [], onUpdated }) {
  const tirs = Array.isArray(match?.tirs_au_but) ? match.tirs_au_but : [];
  const isKnockout = PHASES_ELIMINATOIRES.includes(match?.phase);
  const egalite = Number(match?.score_domicile) === Number(match?.score_exterieur);
  const matchTermine = ["termine", "valide"].includes(match?.statut);
  const editable = isKnockout && egalite && match?.statut === "termine" && !match?.locked && !match?.forfait;
  const [equipe, setEquipe] = useState("domicile");
  const [joueurId, setJoueurId] = useState("");
  const [resultat, setResultat] = useState("marque");
  const [busy, setBusy] = useState(false);
  const [erreur, setErreur] = useState("");
  const [message, setMessage] = useState("");
  if (!isKnockout || (!matchTermine && !tirs.length)) return null;
  const equipeASaisir = tirs.length
    ? (tirs[tirs.length - 1].equipe_concernee === "domicile" ? "exterieur" : "domicile")
    : equipe;
  const listeJoueurs = equipeASaisir === "exterieur" ? joueursExt : joueursDom;
  const prochainVainqueur = vainqueurTirsAuBut(tirs);

  async function enregistrer(e) {
    e.preventDefault();
    if (busy) return;
    setBusy(true); setErreur(""); setMessage("");
    try {
      const updated = await api.ajouterTirAuBut(match.id, {
        equipe_concernee: equipeASaisir,
        joueur_id: Number(joueurId),
        resultat,
      });
      onUpdated?.(updated);
      setEquipe(equipe === "domicile" ? "exterieur" : "domicile");
      setJoueurId("");
      setResultat("marque");
      setMessage("Tir enregistré sans modifier le score du match.");
    } catch (error) {
      setErreur(error.message || "Impossible d’enregistrer ce tir.");
    } finally {
      setBusy(false);
    }
  }

  async function annulerDernier() {
    if (!window.confirm("Retirer le dernier tir de la séance ? Le score normal du match ne changera pas.")) return;
    setBusy(true); setErreur(""); setMessage("");
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
      <ListeTirs tirs={tirs} home={home} away={away} joueurs={Object.fromEntries([...joueursDom, ...joueursExt].map((j) => [j.id, j]))} editable={editable && !busy} onAnnuler={annulerDernier} />
      {editable && !prochainVainqueur ? (
        <form className="compte-form" onSubmit={enregistrer}>
          <div className="comp-grid">
            <label className="field">
              Équipe qui tire
              <select value={equipeASaisir} onChange={(e) => { setEquipe(e.target.value); setJoueurId(""); }} disabled={busy || tirs.length > 0}>
                <option value="domicile">{home}</option>
                <option value="exterieur">{away}</option>
              </select>
            </label>
            <label className="field">
              Tireur
              <select value={joueurId} onChange={(e) => setJoueurId(e.target.value)} disabled={busy} required>
                <option value="" disabled>Choisir un joueur</option>
                {listeJoueurs.map((j) => <option key={j.id} value={j.id}>{j.nom_complet}</option>)}
              </select>
            </label>
            <label className="field">
              Résultat du tir
              <select value={resultat} onChange={(e) => setResultat(e.target.value)} disabled={busy}>
                <option value="marque">Marqué</option>
                <option value="rate">Raté / arrêté</option>
              </select>
            </label>
          </div>
          <p className="muted small">Saisissez les tirs dans leur ordre réel. L’équipe alterne automatiquement et la séance s’arrête dès qu’un vainqueur est mathématiquement certain.</p>
          <button className="btn btn-primary" type="submit" disabled={busy || !joueurId}>
            {busy ? "Enregistrement…" : `Enregistrer le tir n°${tirs.length + 1}`}
          </button>
        </form>
      ) : editable && prochainVainqueur ? (
        <p className="empty">Séance décidée. Validez le résultat pour qualifier le vainqueur.</p>
      ) : !egalite ? (
        <p className="empty">Match de barrage terminé sans égalité : aucune séance de tirs au but à saisir.</p>
      ) : (
        <p className="empty">Séance en lecture seule.</p>
      )}
      {erreur && <p className="erreur">{erreur}</p>}
      {message && <p className="empty">{message}</p>}
    </section>
  );
}
