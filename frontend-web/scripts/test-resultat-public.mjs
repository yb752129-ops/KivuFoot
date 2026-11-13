import assert from "node:assert/strict";
import {
  bilanPublicMatch,
  ETAT_TIRS_OFFICIEL,
  ETAT_TIRS_PROVISOIRE,
  ETAT_TIRS_VAINQUEUR_PROVISOIRE,
  etatTirsAuBut,
  libelleResultat,
  matchsSeanceProvisoire,
  resultatOfficiel,
  texteScoreTirs,
} from "../src/resultatPublic.js";

/** Construit une séance en alternant les équipes, en commençant par `debut`. */
function seance(resultats, debut = "domicile") {
  const autre = debut === "domicile" ? "exterieur" : "domicile";
  return resultats.map((resultat, index) => ({
    ordre: index + 1,
    equipe_concernee: index % 2 === 0 ? debut : autre,
    joueur_id: 100 + index,
    resultat,
  }));
}

const M = "marque";
const R = "rate";

function match(extra = {}) {
  return {
    id: 1,
    phase: "demi",
    statut: "termine",
    date_heure: "2026-11-15T13:00:00Z",
    equipe_domicile_id: 10,
    equipe_exterieur_id: 11,
    score_domicile: 1,
    score_exterieur: 1,
    forfait: false,
    periode: "2",
    tirs_au_but: [],
    ...extra,
  };
}

// --- Mentions « officiel » : seul « valide » est officiel.
assert.equal(resultatOfficiel(match({ statut: "valide" })), true);
for (const statut of ["termine", "en_cours", "programme", "conteste", "annule", undefined]) {
  assert.equal(resultatOfficiel(match({ statut })), false, `statut ${statut}`);
}
assert.equal(resultatOfficiel(null), false);
assert.equal(libelleResultat(match({ statut: "valide" })), "Résultat officiel");
assert.equal(libelleResultat(match({ statut: "termine" })), "Terminé · en attente de validation");
assert.equal(libelleResultat(match({ statut: "en_cours" })), "");
assert.equal(libelleResultat(match({ statut: "programme" })), "");
assert.equal(libelleResultat(undefined), "");

// --- Aucune preuve de séance : aucun état, donc aucune annonce.
assert.equal(etatTirsAuBut(match()), null, "égalité éliminatoire sans aucun tir");
assert.equal(etatTirsAuBut(match({ tirs_au_but: undefined })), null);
assert.equal(etatTirsAuBut(match({ tirs_au_but: null })), null);
assert.equal(etatTirsAuBut(null), null);
assert.equal(etatTirsAuBut(undefined), null);
assert.equal(etatTirsAuBut("match"), null);
assert.equal(etatTirsAuBut(match({ tirs_au_but: [null, {}, { equipe_concernee: "autre", resultat: M }] })), null);

// --- Séance saisie, non décidée : provisoire, sans vainqueur ni mention « en cours ».
const partielle = etatTirsAuBut(match({ tirs_au_but: seance([M, R, M]) }));
assert.equal(partielle.code, ETAT_TIRS_PROVISOIRE);
assert.equal(partielle.provisoire, true);
assert.equal(partielle.officiel, false);
assert.equal(partielle.vainqueur, null);
assert.deepEqual(partielle.score, { domicile: 2, exterieur: 0 });
assert.equal(texteScoreTirs(partielle), "t.a.b. 2–0");
assert.equal(texteScoreTirs(null), "");

// --- Séance décidée mais match non validé : vainqueur provisoire, jamais officiel.
const decidee = seance([M, M, M, M, M, M, M, M, M, R]);
const vainqueurProvisoire = etatTirsAuBut(match({ tirs_au_but: decidee }));
assert.equal(vainqueurProvisoire.code, ETAT_TIRS_VAINQUEUR_PROVISOIRE);
assert.equal(vainqueurProvisoire.vainqueur, "domicile");
assert.equal(vainqueurProvisoire.provisoire, true);
assert.equal(vainqueurProvisoire.officiel, false);

// --- Correction : retirer le dernier tir d'une séance décidée la rend de nouveau non décidée.
const apresAnnulation = etatTirsAuBut(match({ tirs_au_but: decidee.slice(0, -1) }));
assert.equal(apresAnnulation.code, ETAT_TIRS_PROVISOIRE);
assert.equal(apresAnnulation.vainqueur, null);

// --- Match validé : officiel seulement si la séance est décidée.
const officiel = etatTirsAuBut(match({ statut: "valide", tirs_au_but: decidee }));
assert.equal(officiel.code, ETAT_TIRS_OFFICIEL);
assert.equal(officiel.officiel, true);
assert.equal(officiel.provisoire, false);
assert.equal(officiel.vainqueur, "domicile");
assert.equal(etatTirsAuBut(match({ statut: "valide", tirs_au_but: seance([M, R]) })), null, "validé mais séance non décidée : rien d'affirmé");
assert.equal(etatTirsAuBut(match({ statut: "valide", tirs_au_but: [] })), null, "ancien match validé sans séance");

// --- Mort subite.
const sudden = seance([M, M, M, M, M, M, M, M, M, M, M, R]);
assert.equal(etatTirsAuBut(match({ tirs_au_but: sudden.slice(0, 10) })).vainqueur, null);
assert.equal(etatTirsAuBut(match({ tirs_au_but: sudden })).vainqueur, "domicile");
assert.equal(etatTirsAuBut(match({ tirs_au_but: seance([R, M, R, M, R, M, R, M, R, M, M, R]) })).vainqueur, "exterieur");

// --- Toutes les phases à élimination directe sont concernées.
for (const phase of ["barrage", "quart", "demi", "finale"]) {
  assert.equal(etatTirsAuBut(match({ phase, tirs_au_but: seance([M]) })).code, ETAT_TIRS_PROVISOIRE, phase);
}

// --- Cas préservés : poule, forfait, score non égal, statuts sans séance.
assert.equal(etatTirsAuBut(match({ phase: "poule", tirs_au_but: seance([M]) })), null, "nul de poule");
assert.equal(etatTirsAuBut(match({ phase: undefined, tirs_au_but: seance([M]) })), null);
assert.equal(etatTirsAuBut(match({ forfait: true, tirs_au_but: seance([M]) })), null, "forfait");
assert.equal(etatTirsAuBut(match({ score_domicile: 2, score_exterieur: 1, tirs_au_but: seance([M]) })), null, "score non égal");
assert.equal(etatTirsAuBut(match({ score_domicile: null, tirs_au_but: seance([M]) })), null);
assert.equal(etatTirsAuBut(match({ score_domicile: "x", tirs_au_but: seance([M]) })), null);
for (const statut of ["en_cours", "programme", "conteste", "annule"]) {
  assert.equal(etatTirsAuBut(match({ statut, tirs_au_but: seance([M]) })), null, statut);
}

// --- Prolongations : l'état ne dépend pas de la période, ni du règlement.
for (const periode of ["2", "4", null, undefined]) {
  assert.equal(etatTirsAuBut(match({ periode, tirs_au_but: seance([M]) })).code, ETAT_TIRS_PROVISOIRE, `periode ${periode}`);
}
assert.equal(etatTirsAuBut(match({ statut: "en_cours", periode: "3", tirs_au_but: [] })), null, "prolongations en cours");
assert.equal(etatTirsAuBut(match({ periode: "4" })), null, "égalité après prolongations, aucun tir saisi");

// --- Liste des séances provisoires pour l'accueil.
const liste = [
  match({ id: 1, date_heure: "2026-11-15T13:00:00Z", tirs_au_but: seance([M]) }),
  match({ id: 2, date_heure: "2026-11-15T15:00:00Z", tirs_au_but: seance([M, R]) }),
  match({ id: 3, statut: "valide", tirs_au_but: decidee }),
  match({ id: 4, tirs_au_but: [] }),
  match({ id: 5, phase: "poule", tirs_au_but: seance([M]) }),
  match({ id: 6, score_domicile: 2, tirs_au_but: seance([M]) }),
];
assert.deepEqual(matchsSeanceProvisoire(liste).map((item) => item.id), [2, 1]);
assert.deepEqual(matchsSeanceProvisoire(undefined), []);
assert.deepEqual(matchsSeanceProvisoire(null), []);
assert.deepEqual(matchsSeanceProvisoire([]), []);
assert.equal(liste.length, 6, "la liste d'origine n'est pas modifiée");

// --- Bilan public : résultat de CE match séparé de la situation ACTUELLE des équipes.
const barrageValide = match({
  phase: "barrage", statut: "valide", locked: true, score_domicile: 0, score_exterieur: 0,
  tirs_au_but: seance([M, M, R, M, M, M, R, M]),
});

// Deux équipes actives : qualifié (vainqueur aux tirs) puis éliminé à ce tour.
const actives = bilanPublicMatch(barrageValide, { statutDomicile: "actif", statutExterieur: "actif" });
assert.equal(actives.officiel, true);
assert.equal(actives.libelle, "Résultat officiel");
assert.equal(actives.vainqueurTirs, "exterieur");
assert.deepEqual(actives.consequences, [
  { cote: "exterieur", type: "qualifie" },
  { cote: "domicile", type: "elimine", libelle: "barrage" },
]);
assert.deepEqual(actives.situations, []);

// Deux équipes aujourd'hui éliminées : le résultat du match reste, la situation actuelle s'ajoute.
const deuxEliminees = bilanPublicMatch(barrageValide, { statutDomicile: "elimine", statutExterieur: "elimine" });
assert.equal(deuxEliminees.vainqueurTirs, "exterieur", "le vainqueur de ce match ne change pas");
assert.deepEqual(deuxEliminees.consequences, [], "le statut administratif est prioritaire");
assert.deepEqual(deuxEliminees.situations.map((s) => [s.cote, s.libelle]), [
  ["domicile", "Éliminé du tournoi"],
  ["exterieur", "Éliminé du tournoi"],
]);

// Vainqueur d'un ancien match éliminé plus tard : jamais « qualifié », mais bien vainqueur du match.
const vainqueurElimine = bilanPublicMatch(barrageValide, { statutDomicile: "actif", statutExterieur: "elimine" });
assert.equal(vainqueurElimine.vainqueurTirs, "exterieur");
assert.equal(vainqueurElimine.consequences.some((c) => c.type === "qualifie"), false);
assert.deepEqual(vainqueurElimine.consequences, [{ cote: "domicile", type: "elimine", libelle: "barrage" }]);
assert.deepEqual(vainqueurElimine.situations.map((s) => s.cote), ["exterieur"]);

// Disqualifié : mots entiers, sans abréviation.
const disqualifie = bilanPublicMatch(barrageValide, { statutDomicile: "disqualifie", statutExterieur: "actif" });
assert.equal(disqualifie.situations[0].libelle, "Disqualifié du tournoi");
assert.deepEqual(disqualifie.consequences, [{ cote: "exterieur", type: "qualifie" }]);

// Tirs provisoires : aucun vainqueur ni conséquence officiels, même si une équipe est éliminée.
const provisoire = bilanPublicMatch(
  match({ phase: "demi", tirs_au_but: seance([M, M, M, M, M, M, M, M, M, R]) }),
  { statutDomicile: "elimine" },
);
assert.equal(provisoire.officiel, false);
assert.equal(provisoire.libelle, "Terminé · en attente de validation");
assert.equal(provisoire.vainqueurTirs, null);
assert.deepEqual(provisoire.consequences, []);
assert.equal(provisoire.situations.length, 1);

// Match sans tirs : terminé, ou validé sans égalité, ou de poule.
const sansTirs = bilanPublicMatch(match({ phase: "demi" }), {});
assert.equal(sansTirs.vainqueurTirs, null);
assert.deepEqual(sansTirs.consequences, []);
const valideSansEgalite = bilanPublicMatch(
  match({ phase: "quart", statut: "valide", locked: true, score_domicile: 2, score_exterieur: 1 }),
  {},
);
assert.deepEqual(valideSansEgalite.consequences, [{ cote: "exterieur", type: "elimine", libelle: "quart de finale" }]);
assert.equal(valideSansEgalite.vainqueurTirs, null);
assert.deepEqual(bilanPublicMatch(match({ phase: "poule", statut: "valide", locked: true }), {}).consequences, []);

// Entrées invalides ou statuts inconnus : aucune erreur, aucune annonce.
const vide = bilanPublicMatch(null);
assert.equal(vide.officiel, false);
assert.deepEqual(vide.consequences, []);
assert.deepEqual(vide.situations, []);
assert.deepEqual(bilanPublicMatch(barrageValide, { statutDomicile: "retire", statutExterieur: undefined }).situations, []);
assert.deepEqual(bilanPublicMatch(undefined, undefined).situations, []);

console.log("Résultats publics : tests réussis.");
