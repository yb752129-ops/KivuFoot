import { useState } from "react";
import { Link } from "react-router-dom";
import { labelPoste, stripDemo } from "../display.js";
import {
  clePosition,
  lignesAvecPlacements,
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

function normaliserFormation(value) {
  return String(value || "").trim().replace(/[–—]/g, "-");
}

function formationEnregistree(bloc) {
  const formation = normaliserFormation(bloc?.formation);
  return /^\d+(?:-\d+)+$/.test(formation) && slotsPourFormation(formation).length === 11;
}

function formationPourBloc(bloc) {
  return formationEnregistree(bloc) ? normaliserFormation(bloc.formation) : "";
}

function joueursPlaces(bloc) {
  const formation = formationPourBloc(bloc);
  return formation ? lignesAvecPlacements(formation, bloc.titulaires || []) : [];
}

function positionComplete(bloc) {
  const formation = formationPourBloc(bloc);
  const titulaires = Array.isArray(bloc?.titulaires) ? bloc.titulaires : [];
  const places = new Set();
  if (!formation || titulaires.length !== 11) return false;
  for (const joueur of titulaires) {
    const placement = placementDuJoueur(joueur);
    if (!slotValide(formation, placement)) return false;
    const cle = clePosition(placement.ligne_index, placement.position_index);
    if (places.has(cle)) return false;
    places.add(cle);
  }
  return places.size === 11;
}

function statutEquipe(bloc) {
  const nombre = Array.isArray(bloc?.titulaires) ? bloc.titulaires.length : 0;
  return nombre === 0 ? "non-publiee" : "verification";
}

function libelleStatut(statut) {
  return statut === "non-publiee"
    ? "Composition non publiée"
    : "Composition en cours de vérification";
}

function lignesNomEquipe(nom) {
  const mots = String(nom || "Équipe").trim().split(/\s+/).filter(Boolean);
  if (mots.length <= 1) return [mots.join(" ") || "Équipe"];
  const total = mots.join(" ");
  if (total.length <= 18) return [total];
  let meilleur = 1;
  let ecart = Number.POSITIVE_INFINITY;
  for (let index = 1; index < mots.length; index += 1) {
    const gauche = mots.slice(0, index).join(" ");
    const droite = mots.slice(index).join(" ");
    const nouvelEcart = Math.abs(gauche.length - droite.length);
    if (nouvelEcart < ecart) {
      meilleur = index;
      ecart = nouvelEcart;
    }
  }
  return [mots.slice(0, meilleur).join(" "), mots.slice(meilleur).join(" ")];
}

function NomEquipe({ nom, className = "" }) {
  const lignes = lignesNomEquipe(nom);
  return (
    <span className={`feuille-nom-equipe ${className}`.trim()}>
      {lignes[0]}
      {lignes[1] && <><br />{lignes[1]}</>}
    </span>
  );
}

function LogoEquipe({ logo, nom, className = "" }) {
  return (
    <span className={`feuille-logo-equipe ${className}`.trim()} aria-hidden="true">
      {logo ? <img src={logo} alt="" /> : (String(nom || "Équipe").trim().charAt(0).toUpperCase() || "É")}
    </span>
  );
}

function positionsTerrain(nombreLignes, zone = "top") {
  const haut = nombreLignes <= 1
    ? [6]
    : Array.from({ length: nombreLignes }, (_, i) =>
        Math.round(6 + (32 / (nombreLignes - 1)) * i));
  // Les positions d'une composition complète proviennent des slots enregistrés.
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
        ) : null;
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
    lignesAvecPlacements(formationPourBloc(bloc), bloc.titulaires || []).length >= 5
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
          <strong><NomEquipe nom={nomExterieur} /></strong>
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
          <strong><NomEquipe nom={nomDomicile} /></strong>
          <span>{formationDomicile}</span>
        </div>
      </div>
    </section>
  );
}

function JoueurTitulairePublic({ joueur }) {
  return (
    <li className="feuille-titulaire-public">
      <span className="feuille-public-numero" aria-hidden="true">{joueur.numero ?? "—"}</span>
      <span className="feuille-public-identite">
        <strong>{joueur.nom_complet}</strong>
        {labelPoste(joueur.poste) && <small>{labelPoste(joueur.poste)}</small>}
      </span>
    </li>
  );
}

function TitulairesPublic({ bloc, logo, nom }) {
  return (
    <section className="feuille-titulaires-public" aria-label={`Titulaires de ${nom}`}>
      <header className="feuille-titulaires-public-head">
        <LogoEquipe logo={logo} nom={nom} />
        <div>
          <p className="feuille-titulaires-public-kicker">Titulaires</p>
          <h3><NomEquipe nom={nom} /></h3>
        </div>
      </header>
      <ol className="feuille-titulaires-public-list">
        {(bloc.titulaires || []).map((joueur) => <JoueurTitulairePublic key={joueur.id} joueur={joueur} />)}
      </ol>
    </section>
  );
}

function EtatCompositionPublic({ bloc, logo, nom, statut }) {
  return (
    <section className={`feuille-composition-etat is-${statut}`} aria-label={`${nom} : ${libelleStatut(statut)}`}>
      <header className="feuille-composition-etat-head">
        <LogoEquipe logo={logo} nom={nom} />
        <h3><NomEquipe nom={nom} /></h3>
      </header>
      <strong>{libelleStatut(statut)}</strong>
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
              <NomEquipe nom={itemNom} />
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
        <NomEquipe nom={nom} />
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
  const domicile = compo.domicile || { club_nom: "Domicile", titulaires: [], banc: [] };
  const exterieur = compo.exterieur || { club_nom: "Extérieur", titulaires: [], banc: [] };
  const equipes = [
    { id: "domicile", bloc: domicile, logo: logos.domicile || domicile.logo_url, nom: stripDemo(domicile.club_nom) || "Domicile" },
    { id: "exterieur", bloc: exterieur, logo: logos.exterieur || exterieur.logo_url, nom: stripDemo(exterieur.club_nom) || "Extérieur" },
  ];
  const onzeComplet = equipes.every((equipe) => (equipe.bloc.titulaires || []).length === 11);
  const terrainPret = onzeComplet && equipes.every((equipe) => positionComplete(equipe.bloc));

  if (!onzeComplet) {
    return (
      <div className="feuille-compositions-publiques" aria-label="État des compositions">
        {equipes.map((equipe) => (
          <EtatCompositionPublic
            key={equipe.id}
            bloc={equipe.bloc}
            logo={equipe.logo}
            nom={equipe.nom}
            statut={statutEquipe(equipe.bloc)}
          />
        ))}
      </div>
    );
  }

  if (!terrainPret) {
    return (
      <>
        <div className="feuille-titulaires-public-grid">
          {equipes.map((equipe) => (
            <TitulairesPublic key={equipe.id} bloc={equipe.bloc} logo={equipe.logo} nom={equipe.nom} />
          ))}
        </div>
        <RemplacementsPublic domicile={domicile} exterieur={exterieur} logos={logos} staffs={staffs} />
      </>
    );
  }

  return (
    <>
      <TerrainMixte domicile={domicile} exterieur={exterieur} logos={logos} />
      <RemplacementsPublic domicile={domicile} exterieur={exterieur} logos={logos} staffs={staffs} />
    </>
  );
}
