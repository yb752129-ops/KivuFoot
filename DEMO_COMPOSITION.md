# Démonstration isolée — composition professionnelle

Cette démonstration ne contacte pas l’API de production et ne lit aucune donnée du championnat réel.

## Prévisualisation actuellement lancée

- Application : `Composition demo`
- Match DEMO : `9001`
- Page coach : `/coach/matchs/9001/composition`
- Page club : `/club/matchs/9001/composition`
- Démo autonome sans réseau : `demo/composition-demo.html`

## Compte DEMO

- Email : `coach.composition.demo@example.com`
- Mot de passe : `ChangeMoiEnDemo123!`

## Formations disponibles

Les 22 formations suivantes sont sélectionnables sur ordinateur et mobile :

`4-2-3-1`, `4-3-3`, `4-4-2`, `4-1-4-1`, `4-4-1-1`, `4-3-2-1`, `4-5-1`, `4-2-2-2`, `3-5-2`, `3-4-3`, `3-4-2-1`, `3-4-1-2`, `3-6-1`, `3-3-3-1`, `5-3-2`, `5-4-1`, `5-2-3`, `5-3-1-1`, `4-1-2-1-2`, `4-2-1-3`, `4-3-1-2`, `3-2-4-1`.

Le terrain virtuel génère onze emplacements pour chacune. Les titulaires sont répartis selon leur poste ; un fallback contrôlé évite qu’un joueur reste non placé quand le onze est complet.

## Scénarios d’acceptation

1. Ouvrir `Matchs`, puis le match DEMO.
2. Ouvrir `Composition` et vérifier que la formation est sélectionnable par liste déroulante et par raccourcis.
3. Sélectionner seulement **10 titulaires** : l’enregistrement doit être impossible et afficher une erreur indiquant qu’il faut exactement 11 titulaires.
4. Sélectionner **11 titulaires** : les 11 noms et numéros doivent apparaître automatiquement dans la liste et sur le terrain ; aucun titulaire ne doit être indiqué comme « non placé ».
5. Sélectionner **12 titulaires** : la sélection du douzième doit être refusée ; si une requête est forcée, l’API doit répondre HTTP 400.
6. Répéter le test d’affichage pour les **22 formations** ; chaque formation doit produire 11 emplacements.
7. Ajouter des remplaçants et enregistrer une composition complète ; la sauvegarde doit réussir.
8. Tester un numéro de maillot en doublon : la sauvegarde doit être refusée.
9. Tester un numéro invalide et le joueur suspendu DEMO : chaque cas doit être signalé comme bloquant.
10. Vérifier un nom volontairement long, la recherche et les filtres par poste.
11. Actualiser la page : la composition DEMO doit rester visible dans la démo locale.

## Contrôles techniques

- `python -m compileall -q backend/app backend/tests backend/scripts demo`
- `node --check` sur le script extrait de `demo/composition-demo.html`
- `npm ci && npm run build` dans `frontend-web`
- Tests API PostgreSQL : `python -m pytest -q tests/test_coach.py` depuis `backend`, avec le service PostgreSQL de test disponible.

## Important

Le serveur `demo/composition_api.py` conserve les modifications uniquement en mémoire. Un redémarrage remet la démonstration à zéro. Cette étape sert à valider l’interface et le flux utilisateur ; elle ne remplace pas le test PostgreSQL d’une préproduction.

Le script `backend/scripts/seed_composition_demo.py` permet ensuite de créer une démonstration persistante sur une base PostgreSQL séparée. Ne jamais l’exécuter avec l’URL de base de production.

Aucun déploiement de production ne doit être effectué avant validation explicite de la DEMO et réussite des cas 10, 11 et 12 titulaires, des 22 formations, des noms/numéros, des doublons, des suspensions et des numéros invalides.
