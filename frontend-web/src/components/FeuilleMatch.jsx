import { useState } from "react";
import { Link } from "react-router-dom";
import { labelPoste, stripDemo } from "../display.js";
import {
  FORMATION_PAR_DEFAUT,
  clePosition,
  lignesAvecPlacements,
  lignesPourFormation,
  libellePosition,
  placementDuJoueur,
  slotValide,
  slotsPourFormation,
} from "../compositionPositions.js";

function nomCourt(nom) {
  const mots = String(nom || "Joueur").trim().split(/\s+/).filter(Boolean);
  if (mots.length <= 2) return mots.join(" ") || "Joueur";
  return mots.slice(-2).join(" ");
}


function formationPourBloc(bloc) {
  const officielle = String(bloc.formation || "").trim().replace(/[–—]/g, "-");
  if (/^\d+(?:-\d+)+$/.test(officielle) && slotsPourFormation(officielle).length === 11) return officielle;
  return FORMATION_PAR_DEFAUT;
}

function joueursPlaces(bloc) {
  return lignesAvecPlacements(formationPourBloc(bloc), bloc.titulaires || []);
}

function positionComplete(bloc) {
  if (bloc.position_complete === true) return true;
  const formation = formationPourBloc(bloc);
  const titulaires = bloc.titulaires || [];
  const places = new Set();
  if (titulaires.length !== 11) return false;
  for (const joueur of titulaires) {
    const placement = placementDuJoueur(joueur);
    if (!slotValide(formation, placement)) return false;
    const cle = clePosition(placement.ligne_index, placement.position_index);
    if (places.has(cle)) return false;
    places.add(cle);
  }
  return places.size === 11;
}

function positionsTerrain(nombreLignes, zone = "top") {
  const haut = nombreLignes <= 1
    ? [6]
    : Array.from({ length: nombreLignes }, (_, i) =>
        Math.round(6 + (32 / (nombreLignes - 1)) * i));
  // Chaque équipe garde le même sens de lecture : gardien vers le bas
  // de sa moitié, attaque vers l'extrémité opposée.
  return zone === "bottom" ? haut.slice().reverse().map((top) => 100 - top) : haut;
}

function repereJoueur(joueur) {
  if (joueur.numero != null && joueur.numero !== "") return joueur.numero;
  const mot = String(joueur.nom_complet || "").trim().split(/\s+/).filter(Boolean)[0];
  return mot ? mot.charAt(0).toUpperCase() : "";
}

function RangsTerrain({ bloc, zone = "top", inverser = false }) {
  const formation = formationPourBloc(bloc);
  const lignes = joueursPlaces(bloc);
  const ordre = inverser ? [...lignes].reverse() : lignes;
  const positions = positionsTerrain(lignes.length, zone);
  return ordre.map((ligne, ligneIndex) => (
    <div
      className="feuille-terrain-rang"
      key={`${ligne.label}-${ligne.poste}-${ligne.ligneIndex}`}
      style={{ top: `${positions[ligneIndex] ?? 50}%` }}
    >
      {Array.from({ length: ligne.places }).map((_, index) => {
        const joueur = ligne.joueurs[index];
        const positionLabel = libellePosition(formation, ligne.ligneIndex, index);
        return joueur ? (
          <span className="feuille-terrain-joueur" key={joueur.id} title={`${joueur.nom_complet} · ${positionLabel}`}>
            <b>{repereJoueur(joueur)}</b>
            <small>{nomCourt(joueur.nom_complet)}</small>
          </span>
        ) : (
          <span className="feuille-terrain-vide" key={`${ligne.label}-${ligne.ligneIndex}-${index}`} aria-label={`${positionLabel} non renseigné`}>+</span>
        );
      })}
    </div>
  ));
}

function TerrainMixte({ domicile, exterieur, logos = {} }) {
  const nomDomicile = stripDemo(domicile.club_nom) || "Domicile";
  const nomExterieur = stripDemo(exterieur.club_nom) || "Extérieur";
  const formationDomicile = formationPourBloc(domicile);
  const formationExterieur = formationPourBloc(exterieur);
  const dense = [domicile, exterieur].some((bloc) => (
    lignesPourFormation(formationPourBloc(bloc)).length >= 5
  ));
  const logoDomicile = logos.domicile || domicile.logo_url;
  const logoExterieur = logos.exterieur || exterieur.logo_url;
  const positionsIncompletes = [
    { id: "domicile", nom: nomDomicile, bloc: domicile },
    { id: "exterieur", nom: nomExterieur, bloc: exterieur },
  ].filter((equipe) => equipe.bloc.titulaires?.length > 0 && !positionComplete(equipe.bloc));
  return (
    <section className="feuille-tactique feuille-tactique-mixte" aria-label="Terrain tactique des deux équipes">
      <div className="feuille-tactique-head">
        <div>
          <p className="feuille-tactique-kicker">Feuille tactique</p>
          <strong>Les deux équipes sur le même terrain</strong>
        </div>
        <span className="feuille-tactique-note">Lecture seule</span>
      </div>
      {positionsIncompletes.map((equipe) => (
        <div key={equipe.id} className="feuille-position-incomplete" role="status">
          <strong>{equipe.nom} : placement tactique à confirmer</strong>
          <span>Les titulaires sont déclarés, mais la position de chaque joueur n'est pas encore complète. Le terrain ne déplace aucun joueur automatiquement.</span>
          <ul>
            {(equipe.bloc.titulaires || []).map((joueur) => (
              <li key={joueur.id}>{joueur.numero != null ? `N°${joueur.numero} ` : ""}{joueur.nom_complet}</li>
            ))}
          </ul>
        </div>
      ))}
      <div className={`feuille-terrain feuille-terrain-mixte${dense ? " feuille-terrain-dense" : ""}`}>
        {logoExterieur && <img className="feuille-terrain-logo feuille-terrain-logo-away" src={logoExterieur} alt="" aria-hidden="true" />}
        {logoDomicile && <img className="feuille-terrain-logo feuille-terrain-logo-home" src={logoDomicile} alt="" aria-hidden="true" />}
        <div className="feuille-terrain-surface feuille-terrain-surface-away" aria-hidden="true" />
        <div className="feuille-terrain-surface feuille-terrain-surface-home" aria-hidden="true" />
        <div className="feuille-terrain-but feuille-terrain-but-away" aria-hidden="true" />
        <div className="feuille-terrain-but feuille-terrain-but-home" aria-hidden="true" />
        <div className="feuille-terrain-cercle" aria-hidden="true" />
        <div className="feuille-terrain-ligne" aria-hidden="true" />
        <div className="feuille-terrain-team feuille-terrain-team-away">
          {logoExterieur && <img className="feuille-terrain-team-logo" src={logoExterieur} alt="" aria-hidden="true" />}
          <strong>{nomExterieur}</strong>
          <span>{formationExterieur}</span>
        </div>
        <div className="feuille-terrain-rangs feuille-terrain-rangs-away">
          <RangsTerrain bloc={exterieur} zone="top" inverser />
        </div>
        <div className="feuille-terrain-centre" aria-hidden="true" />
        <div className="feuille-terrain-rangs feuille-terrain-rangs-home">
          <RangsTerrain bloc={domicile} zone="bottom" inverser />
        </div>
        <div className="feuille-terrain-team feuille-terrain-team-home">
          {logoDomicile && <img className="feuille-terrain-team-logo" src={logoDomicile} alt="" aria-hidden="true" />}
          <strong>{nomDomicile}</strong>
          <span>{formationDomicile}</span>
        </div>
      </div>

    </section>
  );
}

function RemplacantPublic({ joueur }) {
  const initiales = String(joueur.nom_complet || "?")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((mot) => mot.charAt(0))
    .join("")
    .toUpperCase();
  return (
    <Link to={`/joueurs/${joueur.id}`} className="feuille-remplacant">
      <span className="feuille-remplacant-photo" aria-hidden="true">
        {joueur.photo_url ? <img src={joueur.photo_url} alt="" /> : initiales}
      </span>
      <span className="feuille-remplacant-identite">
        <strong>{joueur.numero != null && <span className="feuille-remplacant-numero">{joueur.numero}</span>}{joueur.nom_complet}</strong>
        {labelPoste(joueur.poste) && <small>{labelPoste(joueur.poste)}</small>}
      </span>
    </Link>
  );
}

function RemplacementsPublic({ domicile, exterieur, logos, staffs }) {
  const equipes = [
    { id: "domicile", bloc: domicile, logo: logos.domicile || domicile.logo_url, staff: staffs.domicile },
    { id: "exterieur", bloc: exterieur, logo: logos.exterieur || exterieur.logo_url, staff: staffs.exterieur },
  ];
  const [equipeId, setEquipeId] = useState("domicile");
  const equipe = equipes.find((item) => item.id === equipeId) || equipes[0];
  const nom = stripDemo(equipe.bloc.club_nom) || "Équipe à nommer";
  const banc = equipe.bloc.banc || [];
  const staff = equipe.bloc.staff || equipe.staff;

  return (
    <section className="feuille-remplacements" aria-label="Remplaçants">
      <div className="feuille-remplacements-selecteur" role="tablist" aria-label="Équipe des remplaçants">
        {equipes.map((item) => {
          const itemNom = stripDemo(item.bloc.club_nom) || "Équipe";
          const actif = item.id === equipeId;
          return (
            <button
              key={item.id}
              type="button"
              className={`feuille-remplacements-equipe${actif ? " actif" : ""}`}
              role="tab"
              aria-selected={actif}
              onClick={() => setEquipeId(item.id)}
            >
              <span className="feuille-remplacements-logo" aria-hidden="true">
                {item.logo ? <img src={item.logo} alt="" /> : itemNom.charAt(0)}
              </span>
              <span>{itemNom}</span>
            </button>
          );
        })}
      </div>
      {staff ? (
        <div className="feuille-remplacements-coach">
          <span className="feuille-photo" aria-hidden="true">
            {staff.photo_url ? <img src={staff.photo_url} alt="" /> : (staff.nom_complet || "?").charAt(0)}
          </span>
          <span className="feuille-remplacements-coach-identite">
            <strong>{staff.nom_complet}</strong>
            <small>{staff.role_label || posteStaff(staff.role)}</small>
          </span>
        </div>
      ) : null}
      <div className="feuille-remplacements-tete">
        <h3 className="feuille-section">Remplaçants</h3>
        <span>{nom}</span>
      </div>
      {banc.length === 0 ? (
        <p className="feuille-vide">Aucun remplaçant déclaré.</p>
      ) : (
        <div className="feuille-remplacants-liste">
          {banc.map((joueur) => <RemplacantPublic key={joueur.id} joueur={joueur} />)}
        </div>
      )}
    </section>
  );
}

function posteStaff(r) {
  const t = String(r || "").replace(/_/g, " ").trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : "";
}

export default function FeuilleMatch({ compo, logos = {}, staffs = {} }) {
  if (!compo) return <p className="empty">Chargement…</p>;
  const domicile = compo.domicile || { titulaires: [], banc: [] };
  const exterieur = compo.exterieur || { titulaires: [], banc: [] };
  const compositionDeclaree = [domicile, exterieur].some(
    (bloc) => Array.isArray(bloc.titulaires) && bloc.titulaires.length > 0
  );
  return (
    <>
      {compositionDeclaree ? (
        <TerrainMixte domicile={domicile} exterieur={exterieur} logos={logos} />
      ) : (
        <div className="feuille-composition-incomplete" role="status">
          <strong>Composition non renseignée</strong>
        </div>
      )}
      <RemplacementsPublic domicile={domicile} exterieur={exterieur} logos={logos} staffs={staffs} />
    </>
  );
}
