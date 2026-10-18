export const FORMATIONS = [
  "4-2-3-1", "4-3-3", "4-4-2", "4-1-4-1", "4-4-1-1", "4-3-2-1", "4-5-1",
  "4-2-2-2", "3-5-2", "3-4-3", "3-4-2-1", "3-4-1-2", "3-6-1", "3-3-3-1",
  "5-3-2", "5-4-1", "5-2-3", "5-3-1-1", "4-1-2-1-2", "4-2-1-3", "4-3-1-2", "3-2-4-1",
];

export const FORMATION_PAR_DEFAUT = "4-3-3";

export function lignesPourFormation(value) {
  const nombres = String(value || "")
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

export function clePosition(ligneIndex, positionIndex) {
  if (ligneIndex == null || positionIndex == null) return "";
  return `${ligneIndex}:${positionIndex}`;
}

export function lireClePosition(value) {
  const [ligne, position] = String(value || "").split(":").map(Number);
  if (!Number.isInteger(ligne) || !Number.isInteger(position) || ligne < 0 || position < 0) return null;
  return { ligne_index: ligne, position_index: position };
}

function libelleCote(positionIndex, places) {
  if (places === 1) return "central";
  if (places === 2) return positionIndex === 0 ? "gauche" : "droit";
  if (places === 3) return ["gauche", "central", "droit"][positionIndex] || `position ${positionIndex + 1}`;
  if (places === 4) return ["gauche", "axe gauche", "axe droit", "droit"][positionIndex] || `position ${positionIndex + 1}`;
  if (places === 5) return ["gauche", "axe gauche", "central", "axe droit", "droit"][positionIndex] || `position ${positionIndex + 1}`;
  return `position ${positionIndex + 1}`;
}

function libelleLigne(lignes, ligneIndex) {
  const ligne = lignes[ligneIndex];
  if (!ligne) return "Position hors formation";
  if (ligneIndex === 0) return "Gardien";
  if (ligne.label === "Défense") return "Défense";
  if (ligne.label === "Attaque") return "Attaque";
  const milieuxAvant = lignes.slice(1, ligneIndex).filter((item) => item.label === "Milieu").length;
  const totalMilieux = lignes.filter((item) => item.label === "Milieu").length;
  if (totalMilieux > 1) {
    if (milieuxAvant === 0) return "Milieu défensif";
    if (milieuxAvant === totalMilieux - 1) return "Milieu offensif";
    return `Milieu ${milieuxAvant + 1}`;
  }
  return "Milieu";
}

export function libellePosition(formation, ligneIndex, positionIndex) {
  const lignes = lignesPourFormation(formation);
  const ligne = lignes[ligneIndex];
  if (!ligne || positionIndex < 0 || positionIndex >= ligne.places) return "Position hors formation";
  return `${libelleLigne(lignes, ligneIndex)} · ${libelleCote(positionIndex, ligne.places)}`;
}

export function slotsPourFormation(formation) {
  const lignes = lignesPourFormation(formation);
  return lignes.flatMap((ligne, ligneIndex) => (
    Array.from({ length: ligne.places }, (_, positionIndex) => ({
      ligne_index: ligneIndex,
      position_index: positionIndex,
      key: clePosition(ligneIndex, positionIndex),
      label: libellePosition(formation, ligneIndex, positionIndex),
      ligne: ligne.label,
    }))
  ));
}

export function slotValide(formation, position) {
  if (!position || position.ligne_index == null || position.position_index == null) return false;
  return slotsPourFormation(formation).some((slot) => (
    slot.ligne_index === position.ligne_index && slot.position_index === position.position_index
  ));
}

export function lignesAvecPlacements(formation, titulaires = []) {
  const lignes = lignesPourFormation(formation);
  const parSlot = new Map();
  titulaires.forEach((joueur) => {
    const placement = placementDuJoueur(joueur);
    if (!slotValide(formation, placement)) return;
    const cle = clePosition(placement.ligne_index, placement.position_index);
    if (!parSlot.has(cle)) parSlot.set(cle, joueur);
  });
  return lignes.map((ligne, ligneIndex) => ({
    ...ligne,
    ligneIndex,
    joueurs: Array.from({ length: ligne.places }, (_, positionIndex) => (
      parSlot.get(clePosition(ligneIndex, positionIndex)) || null
    )),
  }));
}

export function placementDuJoueur(joueur) {
  if (joueur?.ligne_index == null || joueur?.position_index == null) return null;
  return { ligne_index: joueur.ligne_index, position_index: joueur.position_index };
}
