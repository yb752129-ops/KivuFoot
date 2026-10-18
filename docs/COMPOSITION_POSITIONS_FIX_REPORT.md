# Compte rendu — correction du positionnement tactique

## Statut

Correction implémentée dans une copie de travail isolée :
`/home/user/kivufoot-composition-fix`.

Aucun vrai match, aucune composition de production, aucun appel API de production, aucun commit, push ou déploiement n'a été effectué.

## Cause exacte

`Composition.jsx` ne persistait que `joueur_id`, `statut` et `numero`. `pitchRows()` reconstruisait les lignes depuis la formation et le `poste` habituel, puis utilisait le premier titulaire restant lorsqu'une ligne était incomplète. Cela pouvait placer un milieu en défense ou déplacer visuellement d'autres joueurs.

`FeuilleMatch.jsx` reconstruisait aussi le terrain, avec un fallback public différent. Aucune des deux interfaces ne disposait d'une place tactique persistée par match.

## Correction

### Données et API

- Migration additive `backend/alembic/versions/0021_composition_positions.py`.
- Deux colonnes nullable ajoutées à `match_participations` :
  - `ligne_index` : ligne de la formation, `0` pour le gardien ;
  - `position_index` : slot de gauche à droite dans la ligne.
- Contrainte de cohérence sur la paire de champs.
- Contrainte d'unicité par match, équipe et slot.
- `CompositionJoueurIn` accepte et valide les deux champs.
- `CompositionJoueurOut` les restitue.
- `CompositionEquipeOut.position_complete` signale si les 11 titulaires possèdent 11 positions distinctes.
- Le backend refuse une feuille titulaire sans position, une position hors formation ou un slot en doublon.
- Les anciennes participations restent lisibles avec des positions `NULL`; aucune position n'est inventée depuis le poste habituel. Elles sont signalées comme placement incomplet et doivent être repositionnées explicitement.

### Interface club

- Nouveau module partagé `frontend-web/src/compositionPositions.js`.
- Le coach choisit explicitement la position de chaque titulaire.
- Chaque slot vide affiche un bouton `+` ouvrant la liste des joueurs disponibles.
- Une tentative de collision est refusée sans déplacement d'un autre joueur.
- Le remplacement, le déplacement explicite et le retrait restent des actions séparées.
- Changer de formation ne remappe pas silencieusement les anciennes positions : les placements sont remis à attribuer.
- Le poste habituel reste une information de profil et ne contraint plus la place du match.
- Le terrain est affiché du bas vers le haut : gardien en bas, défense au-dessus, milieux ensuite, attaque à l'extrémité opposée.
- La disposition du terrain et du sélecteur est adaptée au portrait et au paysage mobile.
- Les slots encore vides restent rendus comme des slots vides, sans lecture de propriété sur une valeur `null` ; le + reste donc utilisable avant que le onze ne soit complet.
- Le bouton d'enregistrement reste désactivé tant que les 11 titulaires n'ont pas 11 positions valides et distinctes.

### Interface publique

- Le terrain utilise la même projection partagée par slots explicites.
- Chaque moitié est orientée avec le gardien vers le bas de sa moitié et l'attaque vers l'extrémité opposée ; cela ne modifie aucun slot enregistré.
- Aucun fallback par poste n'est utilisé pour une composition positionnée.
- Les anciennes feuilles sans positions affichent les titulaires avec une alerte de placement à confirmer, sans les déplacer automatiquement.
- Le public et l'éditeur club utilisent donc les mêmes `ligne_index` / `position_index`.

## Tests

### Réussis

- `frontend-web`: `npm run test:composition`
  - 4-2-3-1, 4-3-3 et 4-4-2 ;
  - ajout dans un ordre désordonné ;
  - 11 slots distincts ;
  - aucun déplacement ;
  - inversion visuelle attaque → gardien ;
  - simulation d'ajout par `+` sur un slot vide ;
  - projection commune club/public.
- `frontend-web`: `npm run build` — build Vite réussi.
- `backend`: `pytest -q tests/test_composition_positions_unit.py` — **5 passed**.
- `python -m compileall -q app tests alembic/versions/0021_composition_positions.py` — réussi.
- `alembic heads` — `0021_composition_positions` est la tête de migration.
- `git diff --check` — réussi.
- Test navigateur Playwright avec API entièrement interceptée :
  `LD_LIBRARY_PATH=/tmp/kivu-ui-test/libs/usr/lib/x86_64-linux-gnu:/tmp/kivu-ui-test/libs/lib/x86_64-linux-gnu node /home/user/kivufoot-composition-diagnostic/e2e_composition_fix.mjs`
  — **réussi** sur viewport portrait 390×844 ; aucun appel réel et aucun match réel modifié.
  - clics sur `+` pour remplir les slots, déplacement explicite d'un titulaire sans permutation silencieuse ;
  - sauvegarde : un seul `PUT` mocké, avec 11 `ligne_index` / `position_index` non nuls et distincts ;
  - rechargement club identique ;
  - page publique identique : lignes DOM `11 → 8 → 6 → 3 → 2`, gardien en bas et position persistée de `JOUEUR 1` conservée.
  - résultat détaillé : `/home/user/kivufoot-composition-diagnostic/e2e_composition_fix_result.json`.

### Non exécutés jusqu'au bout

Les tests d'intégration API existants et nouveaux (`test_coach.py`, `test_composition_positions.py`) nécessitent le PostgreSQL de test configuré sur `localhost:5433`. Aucun serveur PostgreSQL local n'était disponible dans l'environnement de travail ; ils s'arrêtent donc à l'initialisation de la connexion, avant toute création ou modification de données.

Les tests d'intégration n'ont pas été redirigés vers la production.

## Fichiers modifiés

- `backend/app/models/match.py`
- `backend/app/schemas/match.py`
- `backend/app/routes/matchs.py`
- `backend/app/services/composition_positions.py`
- `backend/app/services/checklist_validation.py`
- `backend/alembic/versions/0021_composition_positions.py`
- `backend/tests/test_coach.py`
- `backend/tests/test_composition_positions.py`
- `backend/tests/test_composition_positions_unit.py`
- `frontend-web/src/compositionPositions.js`
- `frontend-web/src/pages/club/Composition.jsx`
- `frontend-web/src/components/FeuilleMatch.jsx`
- `frontend-web/src/styles.css`
- `frontend-web/package.json`
- `frontend-web/scripts/test-composition-positions.mjs`

## Sécurité et suite

La migration est additive et ne modifie pas les positions des joueurs dans l'effectif. Avant toute mise en production, il faut démarrer un PostgreSQL de test isolé, appliquer la migration, exécuter les tests d'intégration API, puis tester visuellement les trois formations avec une feuille de match de test. Aucune validation, commit, push ou déploiement n'est autorisé avant présentation et validation explicite de ces résultats.
