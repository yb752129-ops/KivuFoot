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


function groupePoste(value) {
  const poste = String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
  if (poste.includes("gard")) return "gardien";
  if (poste.includes("def")) return "defenseur";
  if (poste.includes("mil")) return "milieu";
  if (poste.includes("att") || poste.includes("avant")) return "attaquant";
  return "";
}

function formationPourBloc(bloc) {
  const officielle = String(bloc.formation || "").trim();
  if (/^\d+(?:-\d+)+$/.test(officielle)) return officielle;
  const comptes = ["defenseur", "milieu", "attaquant"].map((poste) => (
    (bloc.titulaires || []).filter((joueur) => groupePoste(joueur.poste) === poste).length
  ));
  return comptes.every((nombre) => nombre > 0) && comptes.reduce((total, nombre) => total + nombre, 0) === 10
    ? comptes.join("-")
    : FORMATION_PAR_DEFAUT;
}

function joueursPlaces(bloc) {
  const titulaires = bloc.titulaires || [];
  const postesConnus = titulaires.some((joueur) => Boolean(groupePoste(joueur.poste)));
  const restants = Object.fromEntries(["gardien", "defenseur", "milieu", "attaquant"].map((poste) => [
    poste,
    titulaires.filter((joueur) => groupePoste(joueur.poste) === poste),
  ]));
  const sansPoste = titulaires.filter((joueur) => !groupePoste(joueur.poste));
  const utilises = new Set();
  return lignesPourFormation(formationPourBloc(bloc)).map((ligne) => {
    const joueurs = [];
    while (joueurs.length < ligne.places) {
      const preferes = (restants[ligne.poste] || []).filter((joueur) => !utilises.has(joueur.id));
      // Lorsque les postes sont renseignés, un joueur ne bascule jamais dans
      // une autre ligne : le gardien reste gardien, la défense reste derrière,
      // et l'attaque reste devant. Les postes absents sont utilisés seulement
      // comme remplissage honnête, sans déplacer un poste connu.
      const fallback = (postesConnus ? sansPoste : titulaires)
        .find((joueur) => !utilises.has(joueur.id));
      const joueur = preferes[0] || fallback;
      if (!joueur) break;
      utilises.add(joueur.id);
      joueurs.push(joueur);
    }
    return { ...ligne, joueurs };
  });
}

function positionsTerrain(nombreLignes, inverser = false) {
  const haut = nombreLignes <= 1
    ? [6]
    : Array.from({ length: nombreLignes }, (_, i) =>
        Math.round(6 + (32 / (nombreLignes - 1)) * i));
  return inverser ? haut.slice().reverse().map((top) => 100 - top) : haut;
}

function repereJoueur(joueur) {
  if (joueur.numero != null && joueur.numero !== "") return joueur.numero;
  const mot = String(joueur.nom_complet || "").trim().split(/\s+/).filter(Boolean)[0];
  return mot ? mot.charAt(0).toUpperCase() : "";
}

function RangsTerrain({ bloc, inverser = false }) {
  const lignes = joueursPlaces(bloc);
  const ordre = inverser ? [...lignes].reverse() : lignes;
  const positions = positionsTerrain(lignes.length, inverser);
  return ordre.map((ligne, ligneIndex) => (
    <div
      className="feuille-terrain-rang"
      key={`${ligne.label}-${ligne.poste}`}
      style={{ top: `${positions[ligneIndex] ?? 50}%` }}
    >
      {Array.from({ length: ligne.places }).map((_, index) => {
        const joueur = ligne.joueurs[index];
        return joueur ? (
          <span className="feuille-terrain-joueur" key={joueur.id} title={`${joueur.nom_complet} · ${labelPoste(joueur.poste) || "Poste non renseigné"}`}>
            <b>{repereJoueur(joueur)}</b>
            <small>{nomCourt(joueur.nom_complet)}</small>
          </span>
        ) : (
          <span className="feuille-terrain-vide" key={`${ligne.label}-${index}`} aria-label={`${ligne.label} non renseigné`}>+</span>
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
  return (
    <section className="feuille-tactique feuille-tactique-mixte" aria-label="Terrain tactique des deux équipes">
      <div className="feuille-tactique-head">
        <div>
          <p className="feuille-tactique-kicker">Feuille tactique</p>
          <strong>Les deux équipes sur le même terrain</strong>
        </div>
        <span className="feuille-tactique-note">Lecture seule</span>
      </div>
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
          <RangsTerrain bloc={exterieur} />
        </div>
        <div className="feuille-terrain-centre" aria-hidden="true" />
        <div className="feuille-terrain-rangs feuille-terrain-rangs-home">
          <RangsTerrain bloc={domicile} inverser />
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
        <small>{labelPoste(joueur.poste) || "Remplaçant"}</small>
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
  const terrainDisponible = domicile.titulaires.length === 11 && exterieur.titulaires.length === 11;
  return (
    <>
      {terrainDisponible && <TerrainMixte domicile={domicile} exterieur={exterieur} logos={logos} />}
      <RemplacementsPublic domicile={domicile} exterieur={exterieur} logos={logos} staffs={staffs} />
    </>
  );
}
