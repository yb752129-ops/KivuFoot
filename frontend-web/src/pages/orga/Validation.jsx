import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { useKivu } from "../../context.jsx";
import { labelPoste, stripDemo } from "../../display.js";

const MOTIFS = [
  ["visage_non_visible", "Visage non visible"],
  ["photo_trop_floue", "Photo trop floue"],
  ["mauvaise_personne", "Mauvaise personne"],
  ["photo_non_conforme", "Photo non conforme"],
  ["autre", "Autre"],
];

export default function OrgaValidation() {
  const { clubsById } = useKivu();
  const [lignes, setLignes] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(0);
  const [rejet, setRejet] = useState(0);
  const [motif, setMotif] = useState("visage_non_visible");

  async function load() {
    const l = await api.photosEnAttente();
    setLignes(l || []);
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function decider(id, ok) {
    setBusy(id);
    setErr("");
    setMsg("");
    try {
      if (ok) {
        await api.validerPhoto(id);
        setMsg("Photo validée : elle est désormais officielle.");
      } else {
        await api.rejeterPhoto(id, motif);
        setMsg("Photo rejetée. L’ancienne photo officielle reste seule visible.");
      }
      setRejet(0);
      await load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(0);
    }
  }

  return (
    <section className="hero">
      <h1>Photos à vérifier</h1>
      <p className="lead">Vous êtes l’autorité sportive : une photo n’est publique qu’après votre validation.</p>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}
      {lignes.length === 0 && <p className="empty">Aucune photo en attente.</p>}
      {lignes.map((p) => (
        <div key={p.id} className="validation-carte">
          <span className="effectif-photo effectif-photo-grande">
            <img src={p.url} alt="" />
          </span>
          <div className="validation-infos">
            <strong>{p.sujet_nom || `Sujet ${p.sujet_id}`}</strong>
            <span className="meta-line">
              {p.sujet_club_id ? stripDemo(clubsById[p.sujet_club_id]?.nom || "Club") : "Staff"}
              {p.sujet_poste ? ` · ${labelPoste(p.sujet_poste) || p.sujet_poste}` : ""}
            </span>
            <span className="meta-line">Proposée par : {p.propose_par || "compte du club"}</span>
            {rejet === p.id ? (
              <div className="validation-actions">
                <label className="field">
                  Motif du rejet
                  <select value={motif} onChange={(e) => setMotif(e.target.value)}>
                    {MOTIFS.map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                </label>
                <button className="btn" type="button" disabled={busy === p.id} onClick={() => decider(p.id, false)}>
                  Confirmer le rejet
                </button>
                <button className="btn" type="button" disabled={busy === p.id} onClick={() => setRejet(0)}>
                  Annuler
                </button>
              </div>
            ) : (
              <div className="validation-actions">
                <button className="btn btn-primary" type="button" disabled={busy === p.id} onClick={() => decider(p.id, true)}>
                  Valider
                </button>
                <button className="btn" type="button" disabled={busy === p.id} onClick={() => setRejet(p.id)}>
                  Rejeter
                </button>
              </div>
            )}
          </div>
        </div>
      ))}
    </section>
  );
}
