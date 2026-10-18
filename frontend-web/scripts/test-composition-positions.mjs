import assert from 'node:assert/strict';
import {
  clePosition,
  lignesAvecPlacements,
  slotValide,
  slotsPourFormation,
} from '../src/compositionPositions.js';

const formations = ['4-2-3-1', '4-3-3', '4-4-2'];
for (const formation of formations) {
  const slots = slotsPourFormation(formation);
  assert.equal(slots.length, 11, `${formation} doit exposer 11 slots`);
  assert.equal(new Set(slots.map((slot) => slot.key)).size, 11, `${formation} ne doit pas avoir de doublon`);
}

// Les joueurs sont insérés dans un ordre volontairement désordonné.
// Leur place reste celle explicitement choisie, sans fallback par poste.
const formation = '4-2-3-1';
const assignments = [
  { id: 'gardien', ligne_index: 0, position_index: 0 },
  { id: 'ailier-gauche', ligne_index: 3, position_index: 0 },
  { id: 'ailier-droit', ligne_index: 3, position_index: 2 },
  { id: 'defenseur-gauche', ligne_index: 1, position_index: 0 },
  { id: 'defenseur-central-gauche', ligne_index: 1, position_index: 1 },
  { id: 'defenseur-central-droit', ligne_index: 1, position_index: 2 },
  { id: 'defenseur-droit', ligne_index: 1, position_index: 3 },
  { id: 'milieu-defensif-gauche', ligne_index: 2, position_index: 0 },
  { id: 'milieu-defensif-droit', ligne_index: 2, position_index: 1 },
  { id: 'attaquant', ligne_index: 4, position_index: 0 },
  { id: 'milieu-offensif', ligne_index: 3, position_index: 1 },
];
const expected = new Set(assignments.map((player) => clePosition(player.ligne_index, player.position_index)));
assert.equal(expected.size, 11);
for (const player of assignments) {
  assert.equal(slotValide(formation, player), true, `${player.id} doit être valide`);
}

const occupied = new Map();
for (const player of assignments) {
  const key = clePosition(player.ligne_index, player.position_index);
  assert.equal(occupied.has(key), false, `le slot ${key} ne doit pas déplacer un joueur`);
  occupied.set(key, player.id);
}
assert.equal(occupied.get('1:0'), 'defenseur-gauche');
assert.equal(occupied.get('2:0'), 'milieu-defensif-gauche');
assert.equal(occupied.get('3:0'), 'ailier-gauche');
assert.equal(occupied.get('4:0'), 'attaquant');

const rows = lignesAvecPlacements(formation, assignments);
assert.deepEqual(rows[1].joueurs.map((player) => player?.id), [
  'defenseur-gauche',
  'defenseur-central-gauche',
  'defenseur-central-droit',
  'defenseur-droit',
]);
assert.deepEqual(rows[2].joueurs.map((player) => player?.id), [
  'milieu-defensif-gauche',
  'milieu-defensif-droit',
]);
assert.deepEqual(rows[3].joueurs.map((player) => player?.id), [
  'ailier-gauche',
  'milieu-offensif',
  'ailier-droit',
]);
assert.deepEqual(rows[4].joueurs.map((player) => player?.id), ['attaquant']);
assert.deepEqual(rows.slice().reverse().map((row) => row.label), [
  'Attaque',
  'Milieu',
  'Milieu',
  'Défense',
  'Gardien',
]);

// Simulation d'un bouton "+" : ajouter un joueur à un slot vide ne
// recompose aucune autre ligne.
const partial = assignments.slice(0, 4);
const beforePlus = lignesAvecPlacements(formation, partial);
const chosenForPlus = assignments[4];
const afterPlus = lignesAvecPlacements(formation, [...partial, chosenForPlus]);
assert.equal(beforePlus[1].joueurs[0].id, 'defenseur-gauche');
assert.equal(afterPlus[1].joueurs[0].id, 'defenseur-gauche');
assert.equal(afterPlus[1].joueurs[1].id, 'defenseur-central-gauche');

for (const otherFormation of ['4-3-3', '4-4-2']) {
  const slots = slotsPourFormation(otherFormation);
  assert.equal(slots.length, 11);
  assert.equal(slots.every((slot) => slotValide(otherFormation, slot)), true);
}

console.log('composition positions: OK (4-2-3-1, 4-3-3, 4-4-2; ordre désordonné, aucun déplacement)');
