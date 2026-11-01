import assert from "node:assert/strict";
import { eliminationClub, libellePhaseFinale, vainqueurMatchEliminatoire } from "../src/phaseFinale.js";
import { scoreTirsAuBut, vainqueurTirsAuBut } from "../src/tirsAuBut.js";

const tirs = [
  { ordre: 1, equipe_concernee: "domicile", resultat: "marque" },
  { ordre: 2, equipe_concernee: "exterieur", resultat: "marque" },
  { ordre: 3, equipe_concernee: "domicile", resultat: "marque" },
  { ordre: 4, equipe_concernee: "exterieur", resultat: "marque" },
  { ordre: 5, equipe_concernee: "domicile", resultat: "marque" },
  { ordre: 6, equipe_concernee: "exterieur", resultat: "marque" },
  { ordre: 7, equipe_concernee: "domicile", resultat: "marque" },
  { ordre: 8, equipe_concernee: "exterieur", resultat: "marque" },
  { ordre: 9, equipe_concernee: "domicile", resultat: "rate" },
  { ordre: 10, equipe_concernee: "exterieur", resultat: "marque" },
];

assert.deepEqual(scoreTirsAuBut(tirs), { domicile: 4, exterieur: 5 });
assert.equal(vainqueurTirsAuBut(tirs), "exterieur");

const barrageValide = {
  id: 41,
  phase: "barrage",
  statut: "valide",
  date_heure: "2026-10-30T15:00:00Z",
  equipe_domicile_id: 12,
  equipe_exterieur_id: 14,
  score_domicile: 1,
  score_exterieur: 1,
  tirs_au_but: tirs,
};

assert.deepEqual(vainqueurMatchEliminatoire(barrageValide), { cote: "exterieur", equipeId: 14 });
assert.equal(eliminationClub([barrageValide], 12)?.libelle, "barrage");
assert.equal(eliminationClub([barrageValide], 14), null);
assert.equal(eliminationClub([{ ...barrageValide, statut: "termine" }], 12), null);
assert.equal(eliminationClub([{ ...barrageValide, phase: "poule" }], 12), null);
assert.equal(libellePhaseFinale("quart"), "quart de finale");

console.log("Phase finale : tests réussis.");
