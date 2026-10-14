import { Link } from "react-router-dom";
import { labelPoste, stripDemo } from "../display.js";

const FORMATION_PAR_DEFAUT = "4-3-3";

function lignesPourFormation(value) {
  const nombres = String(value || FORMATION_PAR_DEFAUT)
    .split("-")
    .map((n) => Number(n))
    .filter((n) => Number.isInteger(n) && n > 0);
  if (nombres.length < 2) return lignesPourFormation(FORMATION_PAR_DEFAUT);
  return [
    { label: "Gardien", poste: "gardien", places: 1 },
    ...nombres.map((places, index) => ({
      label: index === 0 ? "Défense" : index === nombres.length - 1 ? "Attaque" : "Milieu",
      poste: index === 0 ? "defenseur" : index === nombres.length - 1 ? "attaquant" : "milieu",
      places,
    })),
  ];
}

function nomCourt(nom) {
  const mots = String(nom || "Joueur").trim().split(/\s+/).filter(Boolean);
  if (mots.length <= 2) return mots.join(" ") || "Joueur";
  return mots.slice(-2).join(" ");
}

function joueursPlaces(bloc) {
  const titulaires = bloc.titulaires || [];
  const restants = Object.fromEntries(["gardien", "defenseur", "milieu", "attaquant"].map((poste) => [
    poste,
    titulaires.filter((joueur) => joueur.poste === poste),
  ]));
  const utilises = new Set();
  return lignesPourFormation(bloc.formation).map((ligne) => {
    const joueurs = [];
    while (joueurs.length < ligne.places) {
      const preferes = (restants[ligne.poste] || []).filter((joueur) => !utilises.has(joueur.id));
      const joueur = preferes[0] || titulaires.find((candidat) => !utilises.has(candidat.id));
      if (!joueur) break;
      utilises.add(joueur.id);
      joueurs.push(joueur);
    }
    return { ...ligne, joueurs };
  });
}

function JoueurPublic({ joueur }) {
  return (
    <Link to={`/joueurs/${joueur.id}`} className="feuille-public-joueur">
      <span className="feuille-public-numero">{joueur.numero ?? "—"}</span>
      <span className="feuille-public-identite">
        <strong>{joueur.nom_complet}</strong>
        <small>{labelPoste(joueur.poste) || "Poste non renseigné"}</small>
      </span>
    </Link>
  );
}

function RangsTerrain({ bloc, inverser = false }) {
  const lignes = joueursPlaces(bloc);
  const ordre = inverser ? [...lignes].reverse() : lignes;
  return ordre.map((ligne) => (
    <div className="feuille-terrain-rang" key={`${ligne.label}-${ligne.poste}`}>
      {Array.from({ length: ligne.places }).map((_, index) => {
        const joueur = ligne.joueurs[index];
        return joueur ? (
          <span className="feuille-terrain-joueur" key={joueur.id} title={`${joueur.nom_complet} · ${labelPoste(joueur.poste) || "Poste non renseigné"}`}>
            <b>{joueur.numero ?? "—"}</b>
            <small>{nomCourt(joueur.nom_complet)}</small>
          </span>
        ) : (
          <span className="feuille-terrain-vide" key={`${ligne.label}-${index}`} aria-label={`${ligne.label} non renseigné`}>+</span>
        );
      })}
    </div>
  ));
}

function TerrainMixte({ domicile, exterieur }) {
  const nomDomicile = stripDemo(domicile.club_nom) || "Domicile";
  const nomExterieur = stripDemo(exterieur.club_nom) || "Extérieur";
  const formationDomicile = String(domicile.formation || "").trim();
  const formationExterieur = String(exterieur.formation || "").trim();
  return (
    <section className="feuille-tactique feuille-tactique-mixte" aria-label="Terrain tactique des deux équipes">
      <div className="feuille-tactique-head">
        <div>
          <p className="feuille-tactique-kicker">Feuille tactique</p>
          <strong>Les deux équipes sur le même terrain</strong>
        </div>
        <span className="feuille-tactique-note">Lecture seule</span>
      </div>
      <div className="feuille-terrain feuille-terrain-mixte">
        <div className="feuille-terrain-cercle" aria-hidden="true" />
        <div className="feuille-terrain-ligne" aria-hidden="true" />
        <div className="feuille-terrain-team feuille-terrain-team-away">
          <strong>{nomExterieur}</strong>
          <span>{formationExterieur || "4-3-3 · aperçu"}</span>
        </div>
        <div className="feuille-terrain-rangs feuille-terrain-rangs-away">
          <RangsTerrain bloc={exterieur} />
        </div>
        <div className="feuille-terrain-centre" aria-hidden="true">VS</div>
        <div className="feuille-terrain-rangs feuille-terrain-rangs-home">
          <RangsTerrain bloc={domicile} inverser />
        </div>
        <div className="feuille-terrain-team feuille-terrain-team-home">
          <strong>{nomDomicile}</strong>
          <span>{formationDomicile || "4-3-3 · aperçu"}</span>
        </div>
      </div>
      {(!formationDomicile || !formationExterieur) && (
        <p className="feuille-tactique-foot">Le placement utilise un modèle 4-3-3 uniquement pour l’aperçu lorsque la formation officielle n’est pas renseignée.</p>
      )}
    </section>
  );
}

function BlocEquipe({ bloc }) {
  const nom = stripDemo(bloc.club_nom) || "Équipe à nommer";
  const titulaires = bloc.titulaires || [];
  const banc = bloc.banc || [];
  const staff = bloc.staff;
  const complet = titulaires.length === 11;

  return (
    <section className="feuille-equipe">
      <header className="feuille-tete">
        <span className="feuille-logo" aria-hidden="true">
          {bloc.logo_url ? <img className="logo-libre" src={bloc.logo_url} alt="" /> : (nom || "?").charAt(0)}
        </span>
        <span className="feuille-club">
          <strong>{nom}</strong>
          {bloc.formation && <span className="feuille-formation">{bloc.formation}</span>}
        </span>
      </header>
      {titulaires.length === 0 && banc.length === 0 ? (
        <p className="feuille-vide">Composition non publiée.</p>
      ) : !complet ? (
        <div className="feuille-composition-incomplete" role="status">
          <strong>Composition non publiée</strong>
          <span>{titulaires.length} titulaire(s) enregistré(s) : un onze complet de 11 titulaires est requis.</span>
        </div>
      ) : (
        <>
          <div className="feuille-public-listes">
            <div>
              <h3 className="feuille-section">Titulaires · {titulaires.length}/11</h3>
              <ol className="feuille-public-joueurs">
                {titulaires.map((joueur) => <JoueurPublic key={joueur.id} joueur={joueur} />)}
              </ol>
            </div>
            <div>
              <h3 className="feuille-section">Banc</h3>
              {banc.length === 0 ? (
                <p className="feuille-vide">Aucun remplaçant déclaré.</p>
              ) : (
                <ol className="feuille-public-joueurs">
                  {banc.map((joueur) => <JoueurPublic key={joueur.id} joueur={joueur} />)}
                </ol>
              )}
            </div>
          </div>
          <h3 className="feuille-section">Entraîneur</h3>
          {staff ? (
            <span className="feuille-coach">
              <span className="feuille-photo" aria-hidden="true">
                {staff.photo_url ? <img src={staff.photo_url} alt="" /> : (staff.nom_complet || "?").charAt(0)}
              </span>
              <span className="feuille-nom">{staff.nom_complet}</span>
              <span className="feuille-poste">{staff.role_label || posteStaff(staff.role)}</span>
            </span>
          ) : (
            <p className="feuille-vide">Entraîneur à compléter.</p>
          )}
        </>
      )}
    </section>
  );
}

function posteStaff(r) {
  const t = String(r || "").replace(/_/g, " ").trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : "";
}

export default function FeuilleMatch({ compo }) {
  if (!compo) return <p className="empty">Chargement…</p>;
  const domicile = compo.domicile || { titulaires: [], banc: [] };
  const exterieur = compo.exterieur || { titulaires: [], banc: [] };
  const terrainDisponible = domicile.titulaires.length === 11 && exterieur.titulaires.length === 11;
  return (
    <>
      {terrainDisponible && <TerrainMixte domicile={domicile} exterieur={exterieur} />}
      <div className="feuille">
        <BlocEquipe bloc={domicile} />
        <BlocEquipe bloc={exterieur} />
      </div>
    </>
  );
}
