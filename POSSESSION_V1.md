# KivuFoot — Possession V1

Cette couche statistique est additive : elle ne lit ni ne modifie les scores,
buts, cartons, remplacements, compositions, classements, disciplines,
actualités ou comptes.

## Protocole

- Méthode : `TIME_BASED`.
- Protocole : `KIVUFOOT_POSSESSION_V1`.
- `TEAM_A` est toujours l'équipe à domicile ; `TEAM_B` l'équipe extérieure.
- Les seuls états du chronomètre sont `TEAM_A`, `TEAM_B`, `PAUSE`,
  `NOT_STARTED` et `FINISHED`.
- Une passe entre joueurs de la même équipe ne produit aucune commande.
  Duel, déviation ou doute est saisi en `PAUSE`.
- Le temps `PAUSE` est conservé séparément et n'est pas dans le dénominateur.
- Les durées sont persistées en millisecondes et exposées aussi sous les noms
  métier `temps_a`, `temps_b` et `temps_non_attribue` en secondes.

## API

- `GET /api/v1/matchs/{id}/possession` : résumé public strictement filtré.
  Il renvoie `Possession non disponible` tant que le match et la possession
  ne sont pas officiellement validés.
- `GET /api/v1/matchs/{id}/possession/gestion` : détail collector/organisateur.
- `POST /api/v1/matchs/{id}/possession/transition` : commande idempotente du
  collecteur, avec `operation_id` UUID obligatoire.
- `POST /api/v1/matchs/{id}/possession/correction` : correction append-only
  d'un intervalle fermé, réservée à l'organisateur autorisé ou à l'admin.
  L'ancienne valeur, le motif et l'auteur sont conservés.

La mi-temps ferme automatiquement l'intervalle en cours et suspend la
capture en `PAUSE` sans chronométrer le repos. La reprise ne redémarre jamais
A ou B automatiquement : une sélection explicite est requise. La fin du
match ferme la capture ; `FINISHED` est ensuite irréversible. Un forfait ferme la capture
éventuelle mais l'exclut de la publication. Les situations sans règle V1
(prolongation, interruption, report, tirs au but) ne sont pas converties en
temps normal.

## Déploiement

La migration `0017_possession_temps` est additive et est exécutée uniquement
par Render via `backend/start.sh` (`alembic upgrade head`). Aucun match réel
ne reçoit de ligne de possession automatiquement : une ligne est créée au
premier démarrage explicite du chronomètre.

Les tests dédiés couvrent les séquences A→B→A, pauses, mi-temps, temps non
attribué, absence de capture, idempotence, durée négative, fin irréversible,
publication et permissions.
