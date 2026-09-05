import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { labelPoste } from "../../display.js";

function estMineur(iso) {
  if (!iso) return false;
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return false;
  const t = new Date();
  let age = t.getFullYear() - d.getFullYear();
  const m = t.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && t.getDate() < d.getDate())) age -= 1;
  return age < 18;
}

export default function ClubEffectif() {
  const { user } = useAuth();
  const clubId = user?.club_id;
  const [joueurs, setJoueurs] = useState([]);
  const [nomJ, setNomJ] = useState("");
  const [dateJ, setDateJ] = useState("");
  const [posteJ, setPosteJ] = useState("");
  const [parentale, setParentale] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!clubId) return;
    const js = await api.joueurs(clubId);
    setJoueurs(js || []);
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clubId]);

  if (!clubId) {
    return <p className="empty">Aucun club rattaché.</p>;
  }

  async function ajouter(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      if (!nomJ.trim()) throw new Error("Le nom complet est obligatoire.");
      if (!dateJ) throw new Error("Date de naissance : à compléter pour enregistrer.");
      const mineur = estMineur(dateJ);
      if (mineur && !parentale) throw new Error("Autorisation parentale requise pour un mineur.");
      const cree = await api.creerJoueur({
        nom_complet: nomJ.trim(),
        date_naissance: dateJ,
        poste: posteJ || null,
        club_actuel_id: clubId,
        autorisation_parentale: mineur ? true : null,
      });
      setNomJ("");
      setDateJ("");
      setPosteJ("");
      setParentale(false);
      if (cree?.statut_verification === "doublon_suspecte") {
        setMsg("Joueur ajouté — doublon possible. Pas de fusion automatique.");
      } else {
        setMsg("Joueur ajouté.");
      }
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="hero">
      <h1>Effectif</h1>
      <p className="lead">Les joueurs du club. Nom complet obligatoire. Pas la composition d’un match.</p>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}
      {joueurs.length === 0 && <p className="empty">Aucun joueur.</p>}
      {joueurs.map((j) => (
        <Link key={j.id} to={`/club/effectif/${j.id}`} className="avenir-row">
          <span className="avenir-noms">
            <span>{j.nom_complet}</span>
            <span className="meta-line">{labelPoste(j.poste) || "Poste à compléter"}</span>
          </span>
        </Link>
      ))}
      <form className="compte-form" onSubmit={ajouter}>
        <label className="field">
          Nom complet du joueur
          <input value={nomJ} onChange={(e) => setNomJ(e.target.value)} placeholder="à compléter" />
        </label>
        <label className="field">
          Date de naissance
          <input type="date" value={dateJ} onChange={(e) => setDateJ(e.target.value)} />
        </label>
        <label className="field">
          Poste
          <select value={posteJ} onChange={(e) => setPosteJ(e.target.value)}>
            <option value="">à compléter</option>
            <option value="gardien">Gardien</option>
            <option value="defenseur">Défenseur</option>
            <option value="milieu">Milieu</option>
            <option value="attaquant">Attaquant</option>
          </select>
        </label>
        {estMineur(dateJ) && (
          <label className="field-check">
            <input type="checkbox" checked={parentale} onChange={(e) => setParentale(e.target.checked)} />
            Autorisation parentale obtenue
          </label>
        )}
        <button className="btn btn-primary" type="submit" disabled={busy}>Ajouter le joueur</button>
      </form>
    </section>
  );
}
