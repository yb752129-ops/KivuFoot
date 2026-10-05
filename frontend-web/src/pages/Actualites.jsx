import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, getActualiteClientToken } from "../api.js";
import { useActualitesLues } from "../actualitesRead.js";
import { useKivu } from "../context.jsx";

const CATEGORIES = {
  annonce: "Annonce officielle",
  match_competition: "Match / compétition",
  retour_journee: "Retour de journée",
  homme_du_match: "Homme du match",
  performance: "Performance",
  photo_moment: "Photo / moment",
  fair_play: "Fair-play",
  information_importante: "Information importante / incident",
};

function dateTexte(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function estRecente(value) {
  if (!value) return false;
  const age = Date.now() - new Date(value).getTime();
  return age >= 0 && age <= 7 * 24 * 60 * 60 * 1000;
}

function libellePriorite(item) {
  if (item.mise_en_avant) return "À la une";
  if (estRecente(item.date_publication)) return "Récent";
  return "Actualité";
}

export { CATEGORIES, dateTexte, estRecente, libellePriorite };

export default function Actualites() {
  const { competition, saison } = useKivu();
  const [searchParams] = useSearchParams();
  const competitionParam = searchParams.get("competition_id") || "";
  const saisonParam = searchParams.get("saison_id") || "";
  const competitionId = competitionParam || competition?.id || "";
  const saisonId = saisonParam || saison?.id || "";
  const PAGE_SIZE = 50;
  const [items, setItems] = useState([]);
  const [categorie, setCategorie] = useState("");
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const actualitesLues = useActualitesLues();

  async function loadPage(nextOffset = 0, append = false) {
    setLoading(true);
    if (!append) setItems([]);

    try {
      const rows = await api.actualites({
        categorie,
        competitionId,
        saisonId,
        offset: nextOffset,
        limit: PAGE_SIZE,
        clientToken: getActualiteClientToken(),
      });

      const incoming = rows || [];

      setItems((previous) => {
        if (!append) return incoming;
        const seen = new Set(previous.map((item) => item.id));
        return [
          ...previous,
          ...incoming.filter((item) => !seen.has(item.id)),
        ];
      });

      setOffset(nextOffset + incoming.length);
      setHasMore(incoming.length === PAGE_SIZE);
      setErr("");
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPage(0, false);
  }, [categorie, competitionId, saisonId]);

  return (
    <section className="hero actualites-page">
      <div className="actualites-en-tete">
        <div>
          <p className="kicker">Éditorial officiel</p>
          <h1>Actualités</h1>
          <p className="lead">La vie des compétitions, sous l’autorité des organisateurs.</p>
        </div>
        <span className="actualites-sceau">KivuFoot</span>
      </div>
      <div className="actualites-filtres" aria-label="Filtrer les actualités">
        <button type="button" className={!categorie ? "actif" : ""} onClick={() => setCategorie("")}>Toutes</button>
        {Object.entries(CATEGORIES).map(([key, label]) => (
          <button key={key} type="button" className={categorie === key ? "actif" : ""} onClick={() => setCategorie(key)}>
            {label}
          </button>
        ))}
      </div>
      {err && <p className="erreur">{err}</p>}
      {loading && <p className="empty">Chargement…</p>}
      {!loading && items.length === 0 && <p className="empty">Aucune actualité publiée pour l’instant.</p>}
      <div className="actualites-liste">
        {items.map((item) => (
          <article className={`actualite-carte${(item.lu || actualitesLues.has(Number(item.id))) ? "" : " actualite-non-lue"}`} key={item.id}>
            {item.image_principale_url ? (
              <img className="actualite-vignette" src={item.image_principale_url} alt="" />
            ) : (
              <div className="actualite-vignette actualite-vignette-vide">KivuFoot</div>
            )}
            <div className="actualite-carte-corps">
              <p className="actualite-meta">
                <span>{CATEGORIES[item.categorie] || item.categorie}</span>
                <time>{dateTexte(item.date_publication)}</time>
              </p>
              <span className={`actualite-priorite ${item.mise_en_avant ? "actualite-priorite-une" : ""}`}>
                {libellePriorite(item)}
              </span>
              {!(item.lu || actualitesLues.has(Number(item.id))) && <span className="actualite-non-lue-label">Non lue</span>}
              <h2><Link to={`/actualites/${item.id}`}>{item.titre}</Link></h2>
              {item.competition_nom && <p className="actualite-contexte">{item.competition_nom}{item.saison_nom ? ` · ${item.saison_nom}` : ""}</p>}
              <p className="actualite-bas">❤️ {item.like_count || 0} · <Link to={`/actualites/${item.id}`}>Lire l’actualité →</Link></p>
            </div>
          </article>
        ))}
      </div>
      {hasMore && (
        <p className="actualites-plus">
          <button
            className="btn"
            type="button"
            disabled={loading}
            onClick={() => loadPage(offset, true)}
          >
            {loading ? "Chargement…" : "Charger les anciennes actualités"}
          </button>
        </p>
      )}
    </section>
  );
}
