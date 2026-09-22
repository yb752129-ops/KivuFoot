import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { useKivu } from "../../context.jsx";
import { stripDemo } from "../../display.js";

const ETATS = {
  a_completer: "À compléter",
  en_cours: "En cours",
  soumis: "Soumis — à valider",
  a_corriger: "Correction demandée",
  valide: "Validé",
};

export default function OrgaEffectifs() {
  const { saison } = useKivu();
  const [lignes, setLignes] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState("");

  async function load() {
    if (!saison) return;
    try {
      setLignes(await api.effectifsSaison(saison.id));
    } catch (e) {
      setErr(e.message || "Impossible de charger les effectifs.");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [saison?.id]);

  async function valider(ligne) {
    setBusy(ligne.club_id);
    setErr("");
    setMsg("");
    try {
      await api.validerEffectif(saison.id, ligne.club_id);
      setMsg(`Effectif validé : ${stripDemo(ligne.club_nom)}.`);
      await load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy("");
    }
  }

  async function demanderCorrection(ligne) {
    const motif = window.prompt(
      `Motif de correction pour ${stripDemo(ligne.club_nom)} (minimum 10 caractères) :`,
      ligne.motif_retour || "",
    );
    if (motif === null) return;
    if (motif.trim().length < 10) {
      setErr("Le motif de correction doit contenir au moins 10 caractères.");
      return;
    }
    setBusy(ligne.club_id);
    setErr("");
    setMsg("");
    try {
      await api.retourEffectif(saison.id, ligne.club_id, motif.trim());
      setMsg(`Correction demandée à ${stripDemo(ligne.club_nom)}.`);
      await load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy("");
    }
  }

  if (!saison) return <p className="empty">Aucune saison active.</p>;

  const soumis = lignes.filter((l) => l.statut === "soumis").length;
  const valides = lignes.filter((l) => l.statut === "valide").length;

  return (
    <section className="hero">
      <p className="kicker">Organisateurs</p>
      <h1>Effectifs des clubs</h1>
      <p className="lead">
        Les 15 clubs doivent soumettre leur effectif. Les organisateurs valident ou demandent une correction ; KivuFoot ne remplace pas leur décision.
      </p>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}
      <div className="orga-chiffres">
        <div className="orga-chiffre"><strong>{lignes.length}</strong><span>Clubs inscrits</span></div>
        <div className="orga-chiffre"><strong>{soumis}</strong><span>À valider</span></div>
        <div className="orga-chiffre"><strong>{valides}</strong><span>Validés</span></div>
      </div>
      <div className="effectifs-liste">
        {lignes.map((ligne) => (
          <article key={ligne.club_id} className={`effectif-admin-row effectif-admin-${ligne.statut}`}>
            <div className="effectif-admin-tete">
              <strong>{stripDemo(ligne.club_nom)}</strong>
              <span className="effectif-statut">{ETATS[ligne.statut] || ligne.statut}</span>
            </div>
            <div className="meta-line">
              {ligne.total_joueurs} joueur{ligne.total_joueurs === 1 ? "" : "s"}
              {ligne.joueurs_sans_photo > 0 ? ` · ${ligne.joueurs_sans_photo} photo${ligne.joueurs_sans_photo === 1 ? "" : "s"} manquante${ligne.joueurs_sans_photo === 1 ? "" : "s"}` : " · photos présentes"}
            </div>
            {ligne.motif_retour && <p className="effectif-motif">{ligne.motif_retour}</p>}
            <div className="effectif-admin-actions">
              {ligne.statut === "soumis" && (
                <button className="btn btn-primary" type="button" disabled={busy === ligne.club_id} onClick={() => valider(ligne)}>
                  {busy === ligne.club_id ? "…" : "Valider"}
                </button>
              )}
              {(ligne.statut === "soumis" || ligne.statut === "valide") && (
                <button className="linkish" type="button" disabled={busy === ligne.club_id} onClick={() => demanderCorrection(ligne)}>
                  Demander une correction
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
