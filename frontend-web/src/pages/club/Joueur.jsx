import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api.js";
import { labelPoste } from "../../display.js";

const CHAMP_LIBELLE = {
  nom_complet: "Nom complet",
  date_naissance: "Date de naissance",
  poste: "Poste",
};

export default function ClubJoueur() {
  const { id } = useParams();
  const [j, setJ] = useState(null);
  const [propsEnAttente, setPropsEnAttente] = useState([]);
  const [tel, setTel] = useState("");
  const [email, setEmail] = useState("");
  const [champ, setChamp] = useState("nom_complet");
  const [valeur, setValeur] = useState("");
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const d = await api.joueurDetail(id);
    setJ(d);
    setTel(d.telephone || "");
    setEmail(d.email || "");
    const ps = await api.propositions(d.id).catch(() => []);
    setPropsEnAttente((ps || []).filter((p) => p.statut === "en_attente"));
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!j && !err) return <p className="empty">Chargement…</p>;
  if (!j) return <p className="erreur">{err}</p>;

  async function sauverContact(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const d = await api.modifierJoueur(j.id, { telephone: tel.trim() || null, email: email.trim() || null });
      setJ(d);
      setMsg("Téléphone et e-mail enregistrés.");
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function proposer(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      if (!valeur.trim()) throw new Error("Indiquez la nouvelle valeur.");
      await api.proposerJoueur(j.id, champ, valeur.trim());
      setValeur("");
      setMsg("Proposition envoyée. L’organisateur décide. Pas de fusion automatique.");
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="hero">
      <p className="kicker"><Link to="/club/effectif">← Effectif</Link></p>
      <h1>{j.nom_complet}</h1>
      {j.statut_verification === "doublon_suspecte" && (
        <p className="erreur">Doublon possible. Pas de fusion automatique.</p>
      )}
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}

      <div className="sheet id-sheet">
        <div className="id-row"><span>Poste</span><strong>{labelPoste(j.poste) || "à compléter"}</strong></div>
        <div className="id-row"><span>Naissance</span><strong>{j.date_naissance || "à compléter"}</strong></div>
        <div className="id-row"><span>Mineur</span><strong>{j.est_mineur ? "Oui" : "Non"}</strong></div>
      </div>

      <form className="compte-form" onSubmit={sauverContact}>
        <p className="kicker">Contact du club — pas public</p>
        <label className="field">
          Téléphone
          <input value={tel} onChange={(e) => setTel(e.target.value)} placeholder="à compléter" />
        </label>
        <label className="field">
          E-mail
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="à compléter" />
        </label>
        <button className="btn btn-primary" type="submit" disabled={busy}>Enregistrer le contact</button>
      </form>

      <div className="section-head">
        <h2>Proposer une modification</h2>
      </div>
      <p className="lead">Nom, naissance et poste : l’organisateur approuve. Le club ne change pas l’identité tout seul.</p>
      <form className="compte-form" onSubmit={proposer}>
        <label className="field">
          Champ
          <select value={champ} onChange={(e) => { setChamp(e.target.value); setValeur(""); }}>
            <option value="nom_complet">Nom complet</option>
            <option value="date_naissance">Date de naissance</option>
            <option value="poste">Poste</option>
          </select>
        </label>
        {champ === "poste" ? (
          <label className="field">
            Nouvelle valeur
            <select value={valeur} onChange={(e) => setValeur(e.target.value)}>
              <option value="">à compléter</option>
              <option value="gardien">Gardien</option>
              <option value="defenseur">Défenseur</option>
              <option value="milieu">Milieu</option>
              <option value="attaquant">Attaquant</option>
            </select>
          </label>
        ) : champ === "date_naissance" ? (
          <label className="field">
            Nouvelle valeur
            <input type="date" value={valeur} onChange={(e) => setValeur(e.target.value)} />
          </label>
        ) : (
          <label className="field">
            Nouvelle valeur
            <input value={valeur} onChange={(e) => setValeur(e.target.value)} />
          </label>
        )}
        <button className="btn btn-primary" type="submit" disabled={busy}>Envoyer la proposition</button>
      </form>

      {propsEnAttente.length > 0 && (
        <>
          <div className="section-head">
            <h2>En attente ({propsEnAttente.length})</h2>
          </div>
          {propsEnAttente.map((p) => (
            <p key={p.id} className="orga-alerte">
              {CHAMP_LIBELLE[p.champ] || p.champ} : {p.ancienne_valeur || "—"} → {p.nouvelle_valeur}
            </p>
          ))}
        </>
      )}
    </section>
  );
}
