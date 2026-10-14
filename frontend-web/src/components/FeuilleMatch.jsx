import { useState } from "react";
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

function LogoEquipe({ bloc, compact = false }) {
  const nom = stripDemo(bloc.club_nom) || "Équipe";
  return (
    <span className={`feuille-equipe-logo ${compact ? "is-compact" : ""}`} aria-hidden="true">
      {bloc.logo_url ? <img src={bloc.logo_url} alt="" /> : nom.charAt(0).toUpperCase()}
    </span>
  );
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

function RangsTerrain({ bloc }) {
  return joueursPlaces(bloc).map((ligne) => (
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

function TerrainLecture({ bloc }) {
  const nom = stripDemo(bloc.club_nom) || "Équipe";
  const formation = String(bloc.formation || "").trim();
  return (
    <section className="feuille-tactique" aria-label={`Terrain tactique de ${nom}`}>
      <div className="feuille-tactique-head">
        <div>
          <p className="feuille-tactique-kicker">Aperçu tactique</p>
          <strong>{formation || "4-3-3 · aperçu"}</strong>
        </div>
        {!formation && <span className="feuille-tactique-note">Formation non renseignée</span>}
      </div>
      <div className="feuille-terrain">
        <div className="feuille-terrain-cercle" aria-hidden="true" />
        <div className="feuille-terrain-ligne" aria-hidden="true" />
        <div className="feuille-terrain-rangs">
          <RangsTerrain bloc={bloc} />
        </div>
      </div>
      {!formation && <p className="feuille-tactique-foot">Le modèle 4-3-3 sert uniquement à positionner visuellement les 11 joueurs lorsque la formation officielle n’est pas renseignée.</p>}
    </section>
  );
}

function CoachPublic({ staff }) {
  if (!staff) return <p className="feuille-coach-absent">Entraîneur non renseigné.</p>;
  return (
    <div className="feuille-public-coach">
      <span className="feuille-photo" aria-hidden="true">
        {staff.photo_url ? <img src={staff.photo_url} alt="" /> : (staff.nom_complet || "?").charAt(0)}
      </span>
      <span>
        <small>Entraîneur</small>
        <strong>{staff.nom_complet}</strong>
      </span>
    </div>
  );
}

function BlocEquipe({ bloc }) {
  const nom = stripDemo(bloc.club_nom) || "Équipe à nommer";
  const titulaires = bloc.titulaires || [];
  const banc = bloc.banc || [];
  const complet = titulaires.length === 11;

  return (
    <section className="feuille-equipe">
      <header className="feuille-tete">
        <LogoEquipe bloc={bloc} />
        <span className="feuille-club">
          <strong>{nom}</strong>
          <small>{bloc.formation || "Formation non renseignée"}</small>
        </span>
      </header>
      <CoachPublic staff={bloc.staff} />
      {titulaires.length === 0 && banc.length === 0 ? (
        <p className="feuille-vide">Composition non publiée.</p>
      ) : !complet ? (
        <div className="feuille-composition-incomplete" role="status">
          <strong>Composition non publiée</strong>
          <span>{titulaires.length} titulaire(s) enregistré(s) : un onze complet de 11 titulaires est requis.</span>
        </div>
      ) : (
        <>
          <TerrainLecture bloc={bloc} />
          <div className="feuille-public-listes">
            <div>
              <h3 className="feuille-section">Titulaires · {titulaires.length}/11</h3>
              <ol className="feuille-public-joueurs">
                {titulaires.map((joueur) => <JoueurPublic key={joueur.id} joueur={joueur} />)}
              </ol>
            </div>
            <div>
              <h3 className="feuille-section">Remplaçants</h3>
              {banc.length === 0 ? (
                <p className="feuille-vide">Aucun remplaçant déclaré.</p>
              ) : (
                <ol className="feuille-public-joueurs">
                  {banc.map((joueur) => <JoueurPublic key={joueur.id} joueur={joueur} />)}
                </ol>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

export default function FeuilleMatch({ compo }) {
  const [equipeActive, setEquipeActive] = useState("domicile");
  if (!compo) return <p className="empty">Chargement…</p>;
  const domicile = compo.domicile || { titulaires: [], banc: [] };
  const exterieur = compo.exterieur || { titulaires: [], banc: [] };
  const blocActif = equipeActive === "exterieur" ? exterieur : domicile;
  const nomDomicile = stripDemo(domicile.club_nom) || "Domicile";
  const nomExterieur = stripDemo(exterieur.club_nom) || "Extérieur";

  return (
    <section className="feuille-public-composition" aria-label="Compositions du match">
      <div className="feuille-equipes-switcher" role="tablist" aria-label="Choisir l'équipe à consulter">
        <button
          type="button"
          role="tab"
          aria-selected={equipeActive === "domicile"}
          className={equipeActive === "domicile" ? "is-active" : ""}
          onClick={() => setEquipeActive("domicile")}
        >
          <LogoEquipe bloc={domicile} compact />
          <span>{nomDomicile}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={equipeActive === "exterieur"}
          className={equipeActive === "exterieur" ? "is-active" : ""}
          onClick={() => setEquipeActive("exterieur")}
        >
          <LogoEquipe bloc={exterieur} compact />
          <span>{nomExterieur}</span>
        </button>
      </div>
      <div className="feuille">
        <BlocEquipe bloc={blocActif} />
      </div>
    </section>
  );
}
