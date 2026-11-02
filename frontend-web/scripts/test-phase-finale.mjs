import assert from "node:assert/strict";
import {
  eliminationClub,
  libelleCartePhaseFinale,
  libellePhaseFinale,
  numeroterMatchsPhase,
  vainqueurMatchEliminatoire,
} from "../src/phaseFinale.js";
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

const barrages = [
  { id: 71, phase: "barrage", date_heure: "2026-11-01T13:00:00Z" },
  { id: 69, phase: "barrage", date_heure: "2026-10-31T13:45:00Z" },
  { id: 68, phase: "barrage", date_heure: "2026-10-31T12:00:00Z" },
  { id: 70, phase: "barrage", date_heure: "2026-11-01T11:00:00Z" },
];
const numerosBarrage = numeroterMatchsPhase(barrages);
assert.equal(libelleCartePhaseFinale("barrage", numerosBarrage.get(68)), "BARRAGE 1");
assert.equal(libelleCartePhaseFinale("barrage", numerosBarrage.get(69)), "BARRAGE 2");
assert.equal(libelleCartePhaseFinale("barrage", numerosBarrage.get(70)), "BARRAGE 3");
assert.equal(libelleCartePhaseFinale("barrage", numerosBarrage.get(71)), "BARRAGE 4");
assert.equal(libelleCartePhaseFinale("quart", 1), "QUART DE FINALE 1");
assert.equal(libelleCartePhaseFinale("demi", 1), "DEMI-FINALE 1");
assert.equal(libelleCartePhaseFinale("finale", 1), "FINALE 1");

const tirsGcv = [
  { ordre: 1, equipe_concernee: "domicile", resultat: "marque" },
  { ordre: 2, equipe_concernee: "exterieur", resultat: "marque" },
  { ordre: 3, equipe_concernee: "domicile", resultat: "rate" },
  { ordre: 4, equipe_concernee: "exterieur", resultat: "marque" },
  { ordre: 5, equipe_concernee: "domicile", resultat: "rate" },
  { ordre: 6, equipe_concernee: "exterieur", resultat: "marque" },
  { ordre: 7, equipe_concernee: "domicile", resultat: "marque" },
  { ordre: 8, equipe_concernee: "exterieur", resultat: "marque" },
];
assert.deepEqual(scoreTirsAuBut(tirsGcv), { domicile: 2, exterieur: 4 });
assert.equal(vainqueurTirsAuBut(tirsGcv), "exterieur");
const barrageTireAuBut = {
  ...barrageValide,
  id: 71,
  equipe_domicile_id: 9,
  equipe_exterieur_id: 15,
  tirs_au_but: tirsGcv,
};
assert.deepEqual(vainqueurMatchEliminatoire(barrageTireAuBut), { cote: "exterieur", equipeId: 15 });
assert.equal(eliminationClub([barrageTireAuBut], 9)?.libelle, "barrage");

console.log("Phase finale : tests réussis.");
