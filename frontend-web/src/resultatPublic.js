import { eliminationSportiveDansMatch } from "./phaseFinale.js";
import { PHASES_ELIMINATOIRES, scoreTirsAuBut, vainqueurTirsAuBut } from "./tirsAuBut.js";

/** Seul le statut « valide » rend un résultat officiel. */
export function resultatOfficiel(match) {
  return match?.statut === "valide";
}

/** Mention publique d'un résultat terminé : officiel seulement après validation. */
export function libelleResultat(match) {
  if (match?.statut === "valide") return "Résultat officiel";
  if (match?.statut === "termine") return "Terminé · en attente de validation";
  return "";
}

export const ETAT_TIRS_PROVISOIRE = "saisie_provisoire";
export const ETAT_TIRS_VAINQUEUR_PROVISOIRE = "vainqueur_provisoire";
export const ETAT_TIRS_OFFICIEL = "officielle";

function tirsExploitables(match) {
  const tirs = Array.isArray(match?.tirs_au_but) ? match.tirs_au_but : [];
  return tirs.filter(
    (tir) => tir && (tir.equipe_concernee === "domicile" || tir.equipe_concernee === "exterieur"),
  );
}

/**
 * État public d'une séance de tirs au but, déduit des seules données du match.
 *
 * Retourne null dès qu'il n'y a pas de preuve : aucun tir saisi, match de
 * poule, forfait, score non égal, match non terminé, ancienne donnée validée
 * sans séance décidée. On n'annonce jamais « en cours » : seule la présence de
 * tirs est prouvée, pas leur déroulement. Le règlement n'est pas nécessaire :
 * le serveur n'accepte un tir que si toutes ses conditions sont remplies.
 */
export function etatTirsAuBut(match) {
  if (!match || typeof match !== "object") return null;
  if (match.statut !== "termine" && match.statut !== "valide") return null;
  if (!PHASES_ELIMINATOIRES.includes(match.phase)) return null;
  if (match.forfait) return null;
  if (match.score_domicile == null || match.score_exterieur == null) return null;
  const domicile = Number(match.score_domicile);
  const exterieur = Number(match.score_exterieur);
  if (!Number.isFinite(domicile) || !Number.isFinite(exterieur) || domicile !== exterieur) return null;

  const tirs = tirsExploitables(match);
  if (tirs.length === 0) return null;

  const score = scoreTirsAuBut(tirs);
  const vainqueur = vainqueurTirsAuBut(tirs);
  if (resultatOfficiel(match)) {
    if (!vainqueur) return null;
    return { code: ETAT_TIRS_OFFICIEL, score, vainqueur, officiel: true, provisoire: false };
  }
  return {
    code: vainqueur ? ETAT_TIRS_VAINQUEUR_PROVISOIRE : ETAT_TIRS_PROVISOIRE,
    score,
    vainqueur,
    officiel: false,
    provisoire: true,
  };
}

/** Matchs dont une séance est saisie mais pas encore validée, du plus récent au plus ancien. */
export function matchsSeanceProvisoire(matchs = []) {
  return (Array.isArray(matchs) ? matchs : [])
    .filter((match) => etatTirsAuBut(match)?.provisoire)
    .sort((a, b) => (Date.parse(b.date_heure || "") || 0) - (Date.parse(a.date_heure || "") || 0)
      || Number(b.id || 0) - Number(a.id || 0));
}

export function texteScoreTirs(etat) {
  return etat ? `t.a.b. ${etat.score.domicile}–${etat.score.exterieur}` : "";
}

/** Statuts administratifs affichés publiquement, avec des mots entiers (pas d'abréviation). */
export const LIBELLE_STATUT_EQUIPE = {
  elimine: "Éliminé du tournoi",
  disqualifie: "Disqualifié du tournoi",
};
const STATUTS_ADMINISTRATIFS_BLOQUANTS = ["disqualifie", "elimine"];
const COTES = ["domicile", "exterieur"];

/**
 * Sépare ce que dit CE match de la situation ACTUELLE des équipes.
 *
 * - `vainqueurTirs`, `consequences` : issus du match, seulement s'il est validé.
 *   Le statut administratif reste prioritaire : une équipe aujourd'hui éliminée
 *   ou disqualifiée n'est jamais présentée comme « qualifiée », ni comme
 *   « éliminée sportivement ».
 * - `situations` : statut administratif actuel de chaque équipe dans l'édition.
 *   Il peut différer du résultat du match (vainqueur d'un ancien match éliminé
 *   plus tard) sans aucune contradiction.
 */
export function bilanPublicMatch(match, { statutDomicile, statutExterieur } = {}) {
  const etat = etatTirsAuBut(match);
  const vainqueurTirs = etat?.officiel ? etat.vainqueur : null;
  const statuts = {
    domicile: String(statutDomicile || "actif"),
    exterieur: String(statutExterieur || "actif"),
  };

  const consequences = [];
  for (const cote of COTES) {
    const clubId = cote === "domicile" ? match?.equipe_domicile_id : match?.equipe_exterieur_id;
    const bloque = STATUTS_ADMINISTRATIFS_BLOQUANTS.includes(statuts[cote]);
    if (vainqueurTirs === cote && !bloque && match?.phase !== "3e_place") consequences.push({ cote, type: "qualifie" });
    const elimination = match ? eliminationSportiveDansMatch(match, clubId, statuts[cote]) : null;
    if (elimination) consequences.push({ cote, type: "elimine", libelle: elimination.libelle });
  }
  consequences.sort((a, b) => (a.type === b.type ? 0 : a.type === "qualifie" ? -1 : 1));

  const situations = COTES
    .filter((cote) => LIBELLE_STATUT_EQUIPE[statuts[cote]])
    .map((cote) => ({ cote, statut: statuts[cote], libelle: LIBELLE_STATUT_EQUIPE[statuts[cote]] }));

  return {
    officiel: resultatOfficiel(match),
    libelle: libelleResultat(match),
    vainqueurTirs,
    consequences,
    situations,
  };
}
