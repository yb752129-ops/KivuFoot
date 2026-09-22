import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, getActualiteClientToken } from "../api.js";
import { CATEGORIES, dateTexte } from "./Actualites.jsx";

function MatchLien({ match }) {
  if (!match) return null;
  return (
    <aside className="actualite-match">
      <p className="kicker">Match associé · {match.journee || ""}</p>
      <Link to={`/matchs/${match.id}`} className="actualite-match-ligne">
        <span>{match.equipe_domicile_nom || "Domicile"}</span>
        <strong>{match.score_domicile} – {match.score_exterieur}</strong>
        <span>{match.equipe_exterieur_nom || "Extérieur"}</span>
      </Link>
      <p className="actualite-match-meta">
        {match.stade || "Stade non précisé"} · {dateTexte(match.date_heure)} · {match.statut}
      </p>
      <Link className="actualite-match-link" to={`/matchs/${match.id}`}>Voir la fiche du match →</Link>
    </aside>
  );
}

export default function ActualiteDetail({ preview = false }) {
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const token = getActualiteClientToken();

  async function load() {
    try {
      const data = preview
        ? await api.previsualiserActualite(id, token)
        : await api.actualite(id, token);
      setItem(data);
      setErr("");
    } catch (e) {
      setErr(e.message);
    }
  }

  useEffect(() => { load(); }, [id, preview]);

  async function aimer() {
    setBusy(true);
    try {
      const result = await api.aimerActualite(id, token);
      setItem((old) => old ? { ...old, liked: result.liked, like_count: result.like_count } : old);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (err) return <section className="hero"><p className="kicker"><Link to={preview ? "/orga/actualites" : "/actualites"}>← Retour</Link></p><p className="erreur">{err}</p></section>;
  if (!item) return <p className="empty">Chargement…</p>;

  return (
    <article className="hero actualite-detail">
      <p className="kicker"><Link to={preview ? "/orga/actualites" : "/actualites"}>← {preview ? "Gestion des actualités" : "Actualités"}</Link></p>
      {preview && <p className="actualite-preview-bandeau">Prévisualisation — cette actualité n’est pas encore visible du public.</p>}
      <p className="actualite-detail-categorie">{CATEGORIES[item.categorie] || item.categorie}</p>
      <h1>{item.titre}</h1>
      <p className="actualite-detail-date">Publié le {dateTexte(item.date_publication || item.date_creation)} · {item.auteur_nom || "KivuFoot"}</p>
      {(item.competition_nom || item.saison_nom || item.journee) && (
        <p className="actualite-detail-contexte">
          {item.competition_nom || "Compétition"}{item.saison_nom ? ` · ${item.saison_nom}` : ""}{item.journee ? ` · ${item.journee}` : ""}
        </p>
      )}
      {item.images?.length > 0 && (
        <div className="actualite-galerie">
          {item.images.map((image) => (
            <figure key={image.id} className={image.principale ? "actualite-image-principale" : ""}>
              <img src={image.url} alt="" />
              {image.telechargement_autorise && (
                <a href={image.url} download={`kivufoot-actualite-${item.id}-${image.id}`} target="_blank" rel="noreferrer">⬇️ Télécharger</a>
              )}
            </figure>
          ))}
        </div>
      )}
      <div className="actualite-texte">
        {item.texte.split(/\n\s*\n/).map((paragraph, index) => <p key={index}>{paragraph}</p>)}
      </div>
      <MatchLien match={item.match} />
      {item.homme_match && (
        <aside className="actualite-joueur">
          {item.homme_match.joueur_photo_url && <img src={item.homme_match.joueur_photo_url} alt="" />}
          <div>
            <p className="kicker">🏅 Homme du match</p>
            <strong>{item.homme_match.joueur_nom}</strong>
            <span>{item.homme_match.club_nom}</span>
          </div>
        </aside>
      )}
      <div className="actualite-actions">
        <button type="button" className={`actualite-like ${item.liked ? "aime" : ""}`} disabled={busy || preview} onClick={aimer}>
          {item.liked ? "♥ Aimé" : "♡ J’aime"} · {item.like_count || 0}
        </button>
        <small>Résultats validés par les organisateurs et publiés avec KivuFoot.</small>
      </div>
    </article>
  );
}
