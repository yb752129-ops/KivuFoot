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
  const slots = formation ? slotsPourFormation(formation) : [];
  const groupeParSlot = new Map(slots.map((slot) => [slot.key, groupePoste(slot.ligne)]));
  const places = new Set();
  if (!formation || titulaires.length !== 11) return false;
  for (const joueur of titulaires) {
    const placement = placementDuJoueur(joueur);
    if (!slotValide(formation, placement)) return false;
    const cle = clePosition(placement.ligne_index, placement.position_index);
    if (places.has(cle)) return false;
    places.add(cle);
    if (groupePoste(joueur.poste) !== groupeParSlot.get(cle)) return false;
  }
  return places.size === 11;
}

function positionsSaisies(bloc) {
  return (bloc.titulaires || []).some((joueur) => (
    joueur.ligne_index != null || joueur.position_index != null
  ));
}

function dispositionEstimee(bloc) {
  const titulaires = Array.isArray(bloc?.titulaires) ? bloc.titulaires : [];
  if (titulaires.length !== 11) return null;
  const groupes = {
    gardien: [],
    defenseur: [],
    milieu: [],
    attaquant: [],
  };
  titulaires.forEach((joueur) => {
    const groupe = groupePoste(joueur.poste);
    if (groupe) groupes[groupe].push(joueur);
  });
  const totalPostesConnus = Object.values(groupes).reduce((total, joueurs) => total + joueurs.length, 0);
  const lignesCompletes = (
    groupes.gardien.length === 1
    && groupes.defenseur.length > 0
    && groupes.milieu.length > 0
    && groupes.attaquant.length > 0
    && totalPostesConnus === 11
  );
  if (!lignesCompletes) return null;
  return {
    formation: `${groupes.defenseur.length}-${groupes.milieu.length}-${groupes.attaquant.length}`,
    lignes: [
      { label: "Gardien", poste: "gardien", places: 1, ligneIndex: 0, joueurs: groupes.gardien },
      { label: "Défense", poste: "defenseur", places: groupes.defenseur.length, ligneIndex: 1, joueurs: groupes.defenseur },
      { label: "Milieu", poste: "milieu", places: groupes.milieu.length, ligneIndex: 2, joueurs: groupes.milieu },
      { label: "Attaque", poste: "attaquant", places: groupes.attaquant.length, ligneIndex: 3, joueurs: groupes.attaquant },
    ],
  };
}

function modeComposition(bloc) {
  const nombre = Array.isArray(bloc?.titulaires) ? bloc.titulaires.length : 0;
  if (nombre === 0) return "non-publiee";
  if (nombre !== 11) return "verification";
  if (positionComplete(bloc)) return "enregistree";
  if (!positionsSaisies(bloc) && dispositionEstimee(bloc)) return "estimee";
  return "liste";
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
  if (zone === "simple") {
    if (nombreLignes <= 1) return [50];
    return Array.from({ length: nombreLignes }, (_, i) =>
      Math.round(18 + (72 / (nombreLignes - 1)) * i));
  }
  if (nombreLignes <= 1) return zone === "bottom" ? [84] : [14];
  if (zone === "bottom") {
    return Array.from({ length: nombreLignes }, (_, i) =>
      Math.round(58 + (26 / (nombreLignes - 1)) * i));
  }
  return Array.from({ length: nombreLignes }, (_, i) =>
    Math.round(14 + (28 / (nombreLignes - 1)) * i));
}

function repereJoueur(joueur) {
  if (joueur.numero != null && joueur.numero !== "") return joueur.numero;
  const mot = String(joueur.nom_complet || "").trim().split(/\s+/).filter(Boolean)[0];
  return mot ? mot.charAt(0).toUpperCase() : "";
}

function lignesPourTerrain(bloc, mode) {
  return mode === "estimee" ? (dispositionEstimee(bloc)?.lignes || []) : joueursPlaces(bloc);
}

function formationPourTerrain(bloc, mode) {
  return mode === "estimee"
    ? dispositionEstimee(bloc)?.formation || ""
    : formationPourBloc(bloc);
}

function RangsTerrain({ bloc, mode = "enregistree", zone = "top", inverser = false }) {
  const formation = formationPourTerrain(bloc, mode);
  const lignes = lignesPourTerrain(bloc, mode);
  const ordre = inverser ? [...lignes].reverse() : lignes;
  const positions = positionsTerrain(lignes.length, zone);
  return ordre.map((ligne, ligneIndex) => (
    <div
      className="feuille-terrain-rang"
      key={`${ligne.label}-${ligne.poste}-${ligne.ligneIndex ?? ligneIndex}`}
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

function NoteEstimation({ nom }) {
  return (
    <p className="feuille-disposition-estimee" role="note">
      <strong>{nom} · Disposition estimée</strong>
      <span>Positions non saisies : disposition estimée d'après les postes habituels</span>
    </p>
  );
}

function TerrainMixte({ domicile, exterieur, logos = {}, modes = {} }) {
  const nomDomicile = stripDemo(domicile.club_nom) || "Domicile";
  const nomExterieur = stripDemo(exterieur.club_nom) || "Extérieur";
  const modeDomicile = modes.domicile || "enregistree";
  const modeExterieur = modes.exterieur || "enregistree";
  const formationDomicile = formationPourTerrain(domicile, modeDomicile);
  const formationExterieur = formationPourTerrain(exterieur, modeExterieur);
  const dense = [
    { bloc: domicile, mode: modeDomicile },
    { bloc: exterieur, mode: modeExterieur },
  ].some(({ bloc, mode }) => lignesPourTerrain(bloc, mode).length >= 5);
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
      {modeDomicile === "estimee" && <NoteEstimation nom={nomDomicile} />}
      {modeExterieur === "estimee" && <NoteEstimation nom={nomExterieur} />}
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
          <span className={modeExterieur === "estimee" ? "feuille-terrain-formation-estimee" : ""}>
            {formationExterieur}{modeExterieur === "estimee" ? " · estimée" : ""}
          </span>
        </div>
        <div className="feuille-terrain-rangs feuille-terrain-rangs-away">
          <RangsTerrain bloc={exterieur} mode={modeExterieur} zone="top" />
        </div>
        <div className="feuille-terrain-centre" aria-hidden="true" />
        <div className="feuille-terrain-rangs feuille-terrain-rangs-home">
          <RangsTerrain bloc={domicile} mode={modeDomicile} zone="bottom" inverser />
        </div>
        <div className="feuille-terrain-team feuille-terrain-team-home">
          {logoDomicile && <img className="feuille-terrain-team-logo" src={logoDomicile} alt="" aria-hidden="true" />}
          <strong><NomEquipe nom={nomDomicile} /></strong>
          <span className={modeDomicile === "estimee" ? "feuille-terrain-formation-estimee" : ""}>
            {formationDomicile}{modeDomicile === "estimee" ? " · estimée" : ""}
          </span>
        </div>
      </div>
    </section>
  );
}

function TerrainSimple({ equipe }) {
  const nom = equipe.nom;
  const formation = formationPourTerrain(equipe.bloc, equipe.mode);
  const logo = equipe.logo;
  const dense = lignesPourTerrain(equipe.bloc, equipe.mode).length >= 5;
  return (
    <section className="feuille-tactique feuille-tactique-simple" aria-label={`Terrain tactique de ${nom}`}>
      <div className="feuille-tactique-head">
        <div>
          <p className="feuille-tactique-kicker">Feuille tactique</p>
          <strong>{nom}</strong>
        </div>
        <span className="feuille-tactique-note">Lecture seule</span>
      </div>
      {equipe.mode === "estimee" && <NoteEstimation nom={nom} />}
      <div className={`feuille-terrain feuille-terrain-mixte feuille-terrain-simple${dense ? " feuille-terrain-dense" : ""}`}>
        {logo && <img className="feuille-terrain-logo feuille-terrain-logo-away" src={logo} alt="" aria-hidden="true" />}
        <div className="feuille-terrain-surface feuille-terrain-surface-away" aria-hidden="true" />
        <div className="feuille-terrain-surface feuille-terrain-surface-home" aria-hidden="true" />
        <div className="feuille-terrain-but feuille-terrain-but-away" aria-hidden="true" />
        <div className="feuille-terrain-but feuille-terrain-but-home" aria-hidden="true" />
        <div className="feuille-terrain-cercle" aria-hidden="true" />
        <div className="feuille-terrain-ligne" aria-hidden="true" />
        <div className="feuille-terrain-team feuille-terrain-team-away">
          {logo && <img className="feuille-terrain-team-logo" src={logo} alt="" aria-hidden="true" />}
          <strong><NomEquipe nom={nom} /></strong>
          <span className={equipe.mode === "estimee" ? "feuille-terrain-formation-estimee" : ""}>
            {formation}{equipe.mode === "estimee" ? " · estimée" : ""}
          </span>
        </div>
        <div className="feuille-terrain-rangs feuille-terrain-rangs-away">
          <RangsTerrain bloc={equipe.bloc} mode={equipe.mode} zone="simple" inverser />
        </div>
      </div>
    </section>
  );
}

function JoueurTitulairePublic({ joueur }) {
  return (
    <li className="feuille-titulaire-public">
      <span className="feuille-public-numero" aria-hidden="true">{repereJoueur(joueur)}</span>
      <span className="feuille-public-identite">
        <strong>{joueur.nom_complet}</strong>
        <small>{labelPoste(joueur.poste) || "Poste à compléter"}</small>
      </span>
    </li>
  );
}

function TitulairesPublic({ bloc, logo, nom, signalerPoste = false }) {
  return (
    <section className="feuille-titulaires-public" aria-label={`Titulaires de ${nom}`}>
      <header className="feuille-titulaires-public-head">
        <LogoEquipe logo={logo} nom={nom} />
        <div>
          <p className="feuille-titulaires-public-kicker">Titulaires</p>
          <h3><NomEquipe nom={nom} /></h3>
          {signalerPoste && <span className="feuille-titulaires-public-alert">Poste à compléter</span>}
        </div>
      </header>
      <ol className="feuille-titulaires-public-list">
        {(bloc.titulaires || []).map((joueur) => <JoueurTitulairePublic key={joueur.id} joueur={joueur} />)}
      </ol>
    </section>
  );
}

function EtatCompositionPublic({ logo, nom, statut }) {
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
  ].map((equipe) => ({ ...equipe, mode: modeComposition(equipe.bloc) }));
  const nombreDifferentDeOnze = equipes.some((equipe) => (equipe.bloc.titulaires || []).length !== 11);
  const equipesTerrain = equipes.filter((equipe) => ["enregistree", "estimee"].includes(equipe.mode));
  const equipesListe = equipes.filter((equipe) => equipe.mode === "liste");
  const modes = {
    domicile: equipes.find((equipe) => equipe.id === "domicile")?.mode,
    exterieur: equipes.find((equipe) => equipe.id === "exterieur")?.mode,
  };

  if (nombreDifferentDeOnze) {
    const equipesEtat = equipes.filter((equipe) => (
      (equipe.bloc.titulaires || []).length !== 11 || equipe.mode !== "liste"
    ));
    return (
      <>
        {equipesEtat.length > 0 && (
          <div className="feuille-compositions-publiques" aria-label="État des compositions">
            {equipesEtat.map((equipe) => (
              <EtatCompositionPublic
                key={equipe.id}
                logo={equipe.logo}
                nom={equipe.nom}
                statut={equipe.mode === "non-publiee" ? "non-publiee" : "verification"}
              />
            ))}
          </div>
        )}
        {equipesListe.length > 0 && (
          <div className="feuille-titulaires-public-grid">
            {equipesListe.map((equipe) => (
              <TitulairesPublic
                key={equipe.id}
                bloc={equipe.bloc}
                logo={equipe.logo}
                nom={equipe.nom}
                signalerPoste
              />
            ))}
          </div>
        )}
        <RemplacementsPublic domicile={domicile} exterieur={exterieur} logos={logos} staffs={staffs} />
      </>
    );
  }

  if (equipesTerrain.length === 2) {
    return (
      <>
        <TerrainMixte domicile={domicile} exterieur={exterieur} logos={logos} modes={modes} />
        <RemplacementsPublic domicile={domicile} exterieur={exterieur} logos={logos} staffs={staffs} />
      </>
    );
  }

  if (equipesTerrain.length === 1) {
    const equipeTerrain = equipesTerrain[0];
    return (
      <>
        <TerrainSimple equipe={equipeTerrain} />
        <div className="feuille-titulaires-public-grid">
          {equipesListe.map((equipe) => (
            <TitulairesPublic
              key={equipe.id}
              bloc={equipe.bloc}
              logo={equipe.logo}
              nom={equipe.nom}
              signalerPoste={!dispositionEstimee(equipe.bloc)}
            />
          ))}
        </div>
        <RemplacementsPublic domicile={domicile} exterieur={exterieur} logos={logos} staffs={staffs} />
      </>
    );
  }

  return (
    <>
      <div className="feuille-titulaires-public-grid">
        {equipesListe.map((equipe) => (
          <TitulairesPublic
            key={equipe.id}
            bloc={equipe.bloc}
            logo={equipe.logo}
            nom={equipe.nom}
            signalerPoste={!dispositionEstimee(equipe.bloc)}
          />
        ))}
      </div>
      <RemplacementsPublic domicile={domicile} exterieur={exterieur} logos={logos} staffs={staffs} />
    </>
  );
}
