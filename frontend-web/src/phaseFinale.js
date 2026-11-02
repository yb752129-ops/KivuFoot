import { PHASES_ELIMINATOIRES, vainqueurTirsAuBut } from "./tirsAuBut.js";

export const ETAPES_PHASE_FINALE = [
  { id: "barrage", titre: "Barrages", filtre: "Barrages", libelleCarte: "BARRAGE", singulier: "barrage" },
  { id: "quart", titre: "Quarts de finale", filtre: "Quarts", libelleCarte: "QUART DE FINALE", singulier: "quart de finale" },
  { id: "demi", titre: "Demi-finales", filtre: "Demis", libelleCarte: "DEMI-FINALE", singulier: "demi-finale" },
  { id: "finale", titre: "Finale", filtre: "Finale", libelleCarte: "FINALE", singulier: "finale" },
];

const ORDRE_PHASE = new Map(ETAPES_PHASE_FINALE.map((phase, index) => [phase.id, index]));

export function libellePhaseFinale(phaseId) {
  return ETAPES_PHASE_FINALE.find((phase) => phase.id === phaseId)?.singulier || "phase finale";
}

/** Libellé de carte indépendant de l'identifiant technique du match. */
export function libelleCartePhaseFinale(phaseId, numero) {
  const phase = ETAPES_PHASE_FINALE.find((item) => item.id === phaseId);
  if (!phase) return "";
  const index = Number(numero);
  return `${phase.libelleCarte}${Number.isSafeInteger(index) && index > 0 ? ` ${index}` : ""}`;
}

/** Numérote chaque tour chronologiquement, sans exposer les IDs des matchs. */
export function numeroterMatchsPhase(matchs = []) {
  const numeros = new Map();
  const source = Array.isArray(matchs) ? matchs : [];

  for (const phase of ETAPES_PHASE_FINALE) {
    const rencontres = source
      .filter((match) => match?.phase === phase.id)
      .slice()
      .sort((a, b) => {
        const dateA = Date.parse(a.date_heure || "");
        const dateB = Date.parse(b.date_heure || "");
        const dateAValide = Number.isFinite(dateA);
        const dateBValide = Number.isFinite(dateB);
        if (dateAValide !== dateBValide) return dateAValide ? -1 : 1;
        if (dateAValide && dateA !== dateB) return dateA - dateB;
        return Number(a.id || 0) - Number(b.id || 0);
      });

    rencontres.forEach((match, index) => {
      if (match?.id !== undefined && match?.id !== null) {
        numeros.set(Number(match.id), index + 1);
      }
    });
  }

  return numeros;
}

/** Renvoie le vainqueur uniquement pour un match éliminatoire validé. */
export function vainqueurMatchEliminatoire(match) {
  if (!match || match.statut !== "valide" || !PHASES_ELIMINATOIRES.includes(match.phase)) return null;
  if (match.score_domicile == null || match.score_exterieur == null) return null;

  const domicileId = Number(match.equipe_domicile_id);
  const exterieurId = Number(match.equipe_exterieur_id);
  const domicile = Number(match.score_domicile);
  const exterieur = Number(match.score_exterieur);
  if (![domicileId, exterieurId, domicile, exterieur].every(Number.isFinite)) return null;

  if (domicile > exterieur) return { cote: "domicile", equipeId: domicileId };
  if (exterieur > domicile) return { cote: "exterieur", equipeId: exterieurId };

  const coteTirs = vainqueurTirsAuBut(match.tirs_au_but || []);
  if (!coteTirs) return null;
  return {
    cote: coteTirs,
    equipeId: coteTirs === "domicile" ? domicileId : exterieurId,
  };
}

/**
 * Mention dérivée du premier match éliminatoire validé perdu par le club.
 * Ne modifie jamais le statut administratif de l'équipe.
 */
export function eliminationClub(matchs = [], clubId) {
  const idClub = Number(clubId);
  if (!Number.isFinite(idClub)) return null;

  const eliminations = (matchs || []).flatMap((match) => {
    const decision = vainqueurMatchEliminatoire(match);
    if (!decision) return [];
    const domicileId = Number(match.equipe_domicile_id);
    const exterieurId = Number(match.equipe_exterieur_id);
    const perdant = decision.equipeId === domicileId
      ? exterieurId
      : decision.equipeId === exterieurId
        ? domicileId
        : null;
    if (perdant !== idClub) return [];
    return [{ match, phase: match.phase, libelle: libellePhaseFinale(match.phase) }];
  });

  eliminations.sort((a, b) => {
    const rangA = ORDRE_PHASE.get(a.phase) ?? Number.MAX_SAFE_INTEGER;
    const rangB = ORDRE_PHASE.get(b.phase) ?? Number.MAX_SAFE_INTEGER;
    if (rangA !== rangB) return rangA - rangB;
    const dateA = Date.parse(a.match.date_heure || "") || 0;
    const dateB = Date.parse(b.match.date_heure || "") || 0;
    return dateA - dateB || Number(a.match.id || 0) - Number(b.match.id || 0);
  });

  return eliminations[0] || null;
}
