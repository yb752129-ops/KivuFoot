import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { useKivu } from "../../context.jsx";
import { labelPoste, stripDemo } from "../../display.js";

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

export default function OrgaEquipe() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const { saison, rechargerClubs, chargerClubsSaison } = useKivu();
  const bureau = user?.role === "organisateur" || user?.role === "admin";
  const [club, setClub] = useState(null);
  const [joueurs, setJoueurs] = useState([]);
  const [edit, setEdit] = useState(false);
  const [nom, setNom] = useState("");
  const [ville, setVille] = useState("");
  const [stade, setStade] = useState("");
  const [nomJ, setNomJ] = useState("");
  const [dateJ, setDateJ] = useState("");
  const [posteJ, setPosteJ] = useState("");
  const [parentale, setParentale] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const c = await api.club(id);
    setClub(c);
    setNom(c.nom);
    setVille(c.ville || "");
    setStade(c.stade || "");
    const js = await api.joueurs(c.id).catch(() => []);
    setJoueurs(js || []);
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!bureau) return <Navigate to="/orga/matchs" replace />;
  if (!club && !err) return <p className="empty">Chargement…</p>;
  if (!club) return <p className="erreur">{err}</p>;

  async function sauver(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const c = await api.modifierClub(club.id, { nom: nom.trim(), ville: ville.trim(), stade: stade.trim() || null });
      setClub(c);
      await rechargerClubs();
      if (saison) await chargerClubsSaison(saison.id);
      setEdit(false);
      setMsg("Équipe mise à jour.");
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function ajouterJoueur(e) {
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
        club_actuel_id: club.id,
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

  async function desinscrire() {
    if (!saison) return;
    if (!window.confirm("Retirer cette équipe de la compétition ? L’historique des matchs n’est pas effacé.")) return;
    setBusy(true);
    setErr("");
    try {
      await api.desinscrireClub(saison.id, club.id);
      await chargerClubsSaison(saison.id);
      nav("/orga/equipes");
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function supprimer() {
    if (!window.confirm("Supprimer définitivement cette équipe ? Impossible s’il y a des matchs.")) return;
    setBusy(true);
    setErr("");
    try {
      await api.supprimerClub(club.id);
      await rechargerClubs();
      if (saison) await chargerClubsSaison(saison.id);
      nav("/orga/equipes");
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="hero">
      <p className="kicker"><Link to="/orga/equipes">← Équipes</Link></p>
      <h1>{stripDemo(club.nom)}</h1>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}

      {!edit && (
        <>
          <div className="sheet id-sheet">
            <div className="id-row"><span>Ville</span><strong>{club.ville || "à compléter"}</strong></div>
            <div className="id-row"><span>Stade</span><strong>{club.stade || "à compléter"}</strong></div>
            <div className="id-row"><span>Coach</span><strong>à compléter</strong></div>
          </div>
          <p>
            <button className="linkish" type="button" onClick={() => setEdit(true)}>Modifier</button>
            {saison && (
              <>
                {" · "}
                <button className="linkish" type="button" disabled={busy} onClick={desinscrire}>Désinscrire</button>
              </>
            )}
            {" · "}
            <button className="linkish" type="button" disabled={busy} onClick={supprimer}>Supprimer</button>
          </p>
        </>
      )}

      {edit && (
        <form className="compte-form" onSubmit={sauver}>
          <label className="field">Nom<input value={nom} onChange={(e) => setNom(e.target.value)} required /></label>
          <label className="field">Ville / département<input value={ville} onChange={(e) => setVille(e.target.value)} required /></label>
          <label className="field">Stade<input value={stade} onChange={(e) => setStade(e.target.value)} /></label>
          <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "…" : "Enregistrer"}</button>
        </form>
      )}

      <div className="section-head">
        <h2>Effectif ({joueurs.length})</h2>
      </div>
      {joueurs.length === 0 && <p className="empty">Aucun joueur. Nom complet obligatoire.</p>}
      {joueurs.map((j) => (
        <Link key={j.id} to={`/joueurs/${j.id}`} className="avenir-row">
          <span className="avenir-noms">
            <span>{j.nom_complet}</span>
            <span className="meta-line">{labelPoste(j.poste) || "Poste à compléter"}</span>
          </span>
        </Link>
      ))}
      <form className="compte-form" onSubmit={ajouterJoueur}>
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
