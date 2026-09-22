import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api.js";
import { useKivu } from "../../context.jsx";
import { CATEGORIES, dateTexte } from "../Actualites.jsx";

const STATUS = { brouillon: "Brouillons", publie: "Publiées", archive: "Archivées" };
const EMPTY = { titre: "", categorie: "annonce", texte: "", match_id: "", journee: "", club_id: "", joueur_id: "", telechargement_autorise: true };

export default function OrgaActualites() {
  const { competition, saison } = useKivu();
  const [filter, setFilter] = useState("");
  const [items, setItems] = useState([]);
  const [matches, setMatches] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [selectedId, setSelectedId] = useState(null);
  const [files, setFiles] = useState([]);
  const [hmMatch, setHmMatch] = useState("");
  const [hmJoueur, setHmJoueur] = useState("");
  const [hmJoueurs, setHmJoueurs] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    try {
      setItems(await api.actualitesGestion({ statut: filter, competitionId: competition?.id || "" }));
      setErr("");
    } catch (e) { setErr(e.message); }
  }

  useEffect(() => { load(); }, [filter, competition?.id]);
  useEffect(() => {
    if (!saison) { setMatches([]); return; }
    api.matchsGestion(saison.id).then(setMatches).catch(() => setMatches([]));
  }, [saison?.id]);

  function nouveau() {
    setSelectedId(null);
    setForm({ ...EMPTY });
    setFiles([]);
    setMsg("");
    setErr("");
  }

  function edit(item) {
    setSelectedId(item.id);
    setForm({
      titre: item.titre || "",
      categorie: item.categorie || "annonce",
      texte: item.texte || "",
      match_id: item.match_id || "",
      journee: item.journee || "",
      club_id: item.club_id || "",
      joueur_id: item.joueur_id || "",
      telechargement_autorise: item.telechargement_autorise !== false,
    });
    setFiles([]);
    setErr("");
    setMsg("");
  }

  function change(key, value) {
    setForm((old) => ({ ...old, [key]: value }));
    if (key === "match_id") {
      const match = matches.find((row) => String(row.id) === String(value));
      setForm((old) => ({ ...old, match_id: value, journee: match?.journee || old.journee }));
    }
  }

  async function save(e) {
    e.preventDefault();
    setBusy(true); setErr(""); setMsg("");
    try {
      const payload = {
        titre: form.titre,
        categorie: form.categorie,
        texte: form.texte,
        competition_id: competition?.id || null,
        saison_id: saison?.id || null,
        journee: form.journee || null,
        match_id: form.match_id ? Number(form.match_id) : null,
        club_id: form.club_id ? Number(form.club_id) : null,
        joueur_id: form.joueur_id ? Number(form.joueur_id) : null,
        telechargement_autorise: form.telechargement_autorise,
      };
      const saved = selectedId ? await api.modifierActualite(selectedId, payload) : await api.creerActualite(payload);
      if (files.length) {
        for (let i = 0; i < files.length; i += 1) await api.ajouterImageActualite(saved.id, files[i], i === 0);
      }
      setSelectedId(saved.id);
      setFiles([]);
      setMsg("Brouillon enregistré. Il reste invisible jusqu’à la publication.");
      await load();
      const fresh = await api.actualiteGestion(saved.id);
      edit(fresh);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  async function action(id, type) {
    setBusy(true); setErr(""); setMsg("");
    try {
      if (type === "publier") await api.publierActualite(id);
      if (type === "archiver") await api.archiverActualite(id);
      setMsg(type === "publier" ? "Actualité publiée." : "Actualité archivée.");
      await load();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  async function choisirMatchHomme(value) {
    setHmMatch(value); setHmJoueur(""); setHmJoueurs([]);
    const match = matches.find((row) => String(row.id) === String(value));
    if (!match) return;
    try {
      const [dom, ext] = await Promise.all([api.joueurs(match.equipe_domicile_id), api.joueurs(match.equipe_exterieur_id)]);
      setHmJoueurs([...(dom || []), ...(ext || [])]);
    } catch (e) { setErr(e.message); }
  }

  async function designerHomme() {
    if (!hmMatch || !hmJoueur) return;
    setBusy(true); setErr(""); setMsg("");
    try {
      await api.designerHommeDuMatch(hmMatch, hmJoueur);
      setMsg("Homme du match désigné par l’organisateur.");
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  return (
    <section className="hero actualites-gestion">
      <div className="actualites-en-tete">
        <div><p className="kicker">Bureau éditorial</p><h1>Actualités</h1><p className="lead">Créer, vérifier, prévisualiser puis publier.</p></div>
        <button type="button" className="btn btn-primary" onClick={nouveau}>+ Nouvelle actualité</button>
      </div>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}
      <div className="actualites-gestion-filtres">
        <button type="button" className={!filter ? "actif" : ""} onClick={() => setFilter("")}>Toutes</button>
        {Object.entries(STATUS).map(([key, label]) => <button key={key} type="button" className={filter === key ? "actif" : ""} onClick={() => setFilter(key)}>{label}</button>)}
      </div>
      <div className="actualites-gestion-liste">
        {items.map((item) => (
          <div className="actualite-admin-ligne" key={item.id}>
            <div><span className={`statut-pastille statut-${item.statut}`}>{STATUS[item.statut] || item.statut}</span><strong>{item.titre}</strong><small>{CATEGORIES[item.categorie] || item.categorie} · {dateTexte(item.date_publication || item.date_creation)} · ❤️ {item.like_count || 0}</small></div>
            <div className="file-actions">
              <button type="button" className="btn" onClick={() => edit(item)}>Modifier</button>
              <Link className="btn" to={`/orga/actualites/${item.id}/previsualiser`}>Prévisualiser</Link>
              {item.statut === "brouillon" && <button type="button" className="btn btn-primary" disabled={busy} onClick={() => action(item.id, "publier")}>Publier</button>}
              {item.statut === "publie" && <button type="button" className="btn" disabled={busy} onClick={() => action(item.id, "archiver")}>Archiver</button>}
            </div>
          </div>
        ))}
      </div>
      {items.length === 0 && <p className="empty">Aucune actualité dans ce filtre.</p>}

      <form className="phase-box actualite-editeur" onSubmit={save}>
        <p className="kicker">{selectedId ? `Modification #${selectedId}` : "Nouveau brouillon"}</p>
        <label className="field">Titre<input value={form.titre} onChange={(e) => change("titre", e.target.value)} required maxLength={180} /></label>
        <div className="comp-grid">
          <label className="field">Catégorie<select value={form.categorie} onChange={(e) => change("categorie", e.target.value)}>{Object.entries(CATEGORIES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <label className="field">Match associé<select value={form.match_id} onChange={(e) => change("match_id", e.target.value)}><option value="">Aucun</option>{matches.map((match) => <option key={match.id} value={match.id}>#{match.id} · {match.equipe_domicile_id} – {match.equipe_exterieur_id} · {match.score_domicile}–{match.score_exterieur}</option>)}</select></label>
        </div>
        <label className="field">Texte éditorial<textarea value={form.texte} onChange={(e) => change("texte", e.target.value)} required minLength={10} rows={8} /></label>
        <label className="field">Photos <input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(e) => setFiles(Array.from(e.target.files || []))} /><small>La première image devient l’image principale. 10 Mo maximum par image.</small></label>
        <label className="checkbox-line"><input type="checkbox" checked={form.telechargement_autorise} onChange={(e) => change("telechargement_autorise", e.target.checked)} /> Téléchargement public autorisé</label>
        <div className="file-actions"><button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Enregistrement…" : "Enregistrer le brouillon"}</button>{selectedId && <Link className="btn" to={`/orga/actualites/${selectedId}/previsualiser`}>Prévisualiser</Link>}</div>
      </form>

      <div className="phase-box homme-match-box">
        <p className="kicker">Décision officielle</p><h2>Homme du match</h2><p className="lead">La désignation appartient à l’organisateur. KivuFoot ne choisit pas automatiquement.</p>
        <label className="field">Match<select value={hmMatch} onChange={(e) => choisirMatchHomme(e.target.value)}><option value="">Choisir un match terminé</option>{matches.filter((m) => ["termine", "valide"].includes(m.statut)).map((m) => <option key={m.id} value={m.id}>#{m.id} · {m.score_domicile}–{m.score_exterieur}</option>)}</select></label>
        <label className="field">Joueur<select value={hmJoueur} onChange={(e) => setHmJoueur(e.target.value)} disabled={!hmMatch}><option value="">Choisir le joueur</option>{hmJoueurs.map((joueur) => <option key={joueur.id} value={joueur.id}>{joueur.nom_complet}</option>)}</select></label>
        <button type="button" className="btn btn-primary" disabled={busy || !hmMatch || !hmJoueur} onClick={designerHomme}>Désigner officiellement</button>
      </div>
    </section>
  );
}
