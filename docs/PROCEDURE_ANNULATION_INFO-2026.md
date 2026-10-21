# Annulation réversible — INFO-2026 / G.G.T–GRF

## Décision technique

L'ancien statut `conteste` n'est pas une annulation réversible : il masque le
match des vues publiques et du classement, mais ne conserve ni motif
spécifique, ni état précédent, ni action de rétablissement dédiée.

Le patch ajoute donc :

- `statut = annule` ;
- `POST /api/v1/matchs/{id}/annuler` ;
- `POST /api/v1/matchs/{id}/retablir` ;
- motif par défaut : `Décision de l'organisation` ;
- état précédent, verrou précédent, auteur et date conservés sur la ligne du
  match ;
- audit `UPDATE` avec utilisateur, date, ancien/nouveau statut et motif ;
- reconstruction atomique des `StatistiqueJoueur` depuis les seuls matchs
  `valide`.

La ligne `matchs` et les lignes `evenements_match` ne sont jamais supprimées.
Un match `annule` est absent des matchs publics, événements publics,
classement, buts/passes, statistiques joueur, discipline, éligibilité,
progression et actualités publiques rattachées au match.

## Procédure Termux — à exécuter manuellement

Les commandes ci-dessous sont une procédure. Elles n'ont pas été exécutées
par l'agent.

### 1. Sauvegarde PostgreSQL avant toute modification

```sh
cd /data/data/com.termux/files/home/kivufoot
export BACKUP="backups/kivufoot-avant-annulation-$(date -u +%Y%m%dT%H%M%SZ).dump"
mkdir -p backups
pg_dump --dbname="$DATABASE_URL" --format=custom --file="$BACKUP"
ls -lh "$BACKUP"
```

### 2. Vérifier puis appliquer le patch

Depuis la racine du dépôt, avec une vérification explicite des fichiers :

```sh
git apply --check kivufoot-annulation-reversible.patch
git apply kivufoot-annulation-reversible.patch

git diff --check
git status --short
```

Le fichier `kivufoot-annulation-reversible.patch` est un livrable de
transfert ; il ne doit pas être ajouté au commit applicatif.

### 3. Migration, vérifications et build

```sh
cd backend
python -m alembic current
python -m alembic upgrade head
python -m compileall -q app alembic/versions
pytest -q

cd ../frontend-web
npm run build
npm run test:composition
cd ..
```

La migration attendue est :

```text
0024_role_coach_to_club -> 0025_match_annulation
```

Ne pas relancer manuellement une migration déjà présente : `alembic upgrade
head` est idempotent.

### 4. Retrouver l'identifiant sans modifier les données

Adapter `DATABASE_URL` si nécessaire. Cette requête est en lecture seule :

```sh
psql "$DATABASE_URL" -c "
SELECT m.id, c.nom AS competition, s.nom AS saison,
       cd.nom AS domicile, ce.nom AS exterieur,
       m.journee, m.date_heure, m.score_domicile, m.score_exterieur,
       m.statut, m.locked
FROM matchs m
JOIN saisons s ON s.id = m.saison_id
JOIN competitions c ON c.id = s.competition_id
LEFT JOIN clubs cd ON cd.id = m.equipe_domicile_id
LEFT JOIN clubs ce ON ce.id = m.equipe_exterieur_id
WHERE (c.nom ILIKE '%INFO-2026%' OR s.nom ILIKE '%INFO-2026%')
  AND ((cd.nom = 'G.G.T' AND ce.nom = 'GRF')
       OR (cd.nom = 'GRF' AND ce.nom = 'G.G.T'))
ORDER BY m.date_heure, m.id;
"
```

Vérifier visuellement la ligne `INFO-2026 – G.G.T-GRF`, score `0–3`,
statut `valide`, heure `10:00`, puis définir uniquement son identifiant :

```sh
export MATCH_ID="<identifiant vérifié>"
export API="https://kivufoot.onrender.com/api/v1"
export TOKEN="<jeton Bearer d'un compte admin/organisateur autorisé>"
```

### 5. Contrôles avant action

Conserver les résultats de ces commandes pour comparaison :

```sh
psql "$DATABASE_URL" -c "
SELECT id, statut, score_domicile, score_exterieur, locked,
       statut_avant_annulation, annule_motif, annule_par_id, annule_at
FROM matchs WHERE id = $MATCH_ID;
"

psql "$DATABASE_URL" -c "
SELECT COUNT(*) AS evenements_conserves
FROM evenements_match WHERE match_id = $MATCH_ID;
"

psql "$DATABASE_URL" -c "
SELECT COUNT(*) AS participations_conservees
FROM match_participations WHERE match_id = $MATCH_ID;
"
```

### 6. Annuler par l'action auditée

Cette requête HTTP est l'action métier ; elle ne supprime ni le match ni ses
événements :

```sh
curl -fsS -X POST "$API/matchs/$MATCH_ID/annuler" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"motif":"Décision de l'organisation"}'
```

Contrôler immédiatement :

```sh
curl -fsS "$API/matchs/$MATCH_ID" || true
psql "$DATABASE_URL" -c "
SELECT id, statut, score_domicile, score_exterieur, locked,
       statut_avant_annulation, annule_motif, annule_par_id, annule_at
FROM matchs WHERE id = $MATCH_ID;
"
psql "$DATABASE_URL" -c "
SELECT COUNT(*) AS evenements_apres_annulation
FROM evenements_match WHERE match_id = $MATCH_ID;
"
psql "$DATABASE_URL" -c "
SELECT id, user_id, action, old_data, new_data, created_at
FROM audit_log
WHERE table_name = 'matchs' AND record_id = $MATCH_ID
ORDER BY id DESC LIMIT 2;
"
```

Le détail public et `/evenements-publics` doivent répondre `404`; le match ne
doit plus apparaître dans `GET /matchs`. La consultation de gestion reste
possible pour permettre l'audit et le rétablissement.

### 7. Vérifier les effets dérivés

```sh
export SAISON_ID="<saison_id vérifié>"
curl -fsS "$API/classement?saison_id=$SAISON_ID" > /tmp/classement-apres-annulation.json
curl -fsS "$API/stats/meilleurs-buteurs?saison_id=$SAISON_ID&limit=100" > /tmp/buteurs-apres-annulation.json
curl -fsS "$API/stats/meilleurs-passeurs?saison_id=$SAISON_ID&limit=100" > /tmp/passeurs-apres-annulation.json
```

Résultats attendus pour cette correction :

- `G.G.T-GRF` : `J3`, `5 pts`, `G1 N2 P0`, `BP4`, `BC3`, `DIFF +1` ;
- `+243(SAE)` reste en tête avec `7 pts` ;
- `INFO-2026` : `J0` dans la ligne concernée ;
- aucun autre club ne doit changer dans le classement. Pour documenter toute
  différence inattendue, comparer les snapshots avant/après de `classement`
  sur `club_id`, `matchs_joues`, `points`, `victoires`, `nuls`, `defaites`,
  `buts_marques`, `buts_encaisses` et `difference_buts`.

Les seules contributions joueur potentiellement retirées proviennent des
participations et événements du match annulé. Une vérification SQL permet de
les lister sans toucher aux faits :

```sh
psql "$DATABASE_URL" -c "
SELECT DISTINCT mp.club_id, c.nom AS club, mp.joueur_id
FROM match_participations mp
LEFT JOIN clubs c ON c.id = mp.club_id
WHERE mp.match_id = $MATCH_ID
ORDER BY mp.club_id, mp.joueur_id;
"
psql "$DATABASE_URL" -c "
SELECT id, type, joueur_id, joueur_secondaire_id, statut_validation, refuse
FROM evenements_match
WHERE match_id = $MATCH_ID
ORDER BY id;
"
```

### 8. Rétablir si nécessaire

Le rétablissement utilise l'état précédent mémorisé ; il ne faut pas modifier
le statut directement en SQL :

```sh
curl -fsS -X POST "$API/matchs/$MATCH_ID/retablir" \
  -H "Authorization: Bearer $TOKEN"
```

Recontrôler le statut et les mêmes snapshots. Pour le match demandé, le statut
et le verrou doivent redevenir ceux qui précédaient l'annulation (`valide` et
`locked=true`) et les contributions officielles doivent réapparaître.

## Rollback du déploiement

1. Si une annulation est active, la rétablir par l'action HTTP ci-dessus avant
   de tenter le downgrade : la migration refuse volontairement de supprimer
   un état `annule` encore présent.
2. Arrêter le service applicatif si nécessaire.
3. Après validation de la sauvegarde et de la liste des changements :

```sh
cd /data/data/com.termux/files/home/kivufoot
python -m alembic downgrade 0024_role_coach_to_club
git apply --check -R kivufoot-annulation-reversible.patch
git apply -R kivufoot-annulation-reversible.patch
```

4. En dernier recours, restaurer le dump validé avec `pg_restore` dans la base
   arrêtée et documenter l'opération :

```sh
pg_restore --clean --if-exists --dbname="$DATABASE_URL" "$BACKUP"
```

## Commit et push manuels

Après les contrôles seulement, ajouter les fichiers explicitement et ne pas
ajouter le patch de transfert :

```sh
git add \
  backend/alembic/versions/0025_match_annulation.py \
  backend/app/models/enums.py \
  backend/app/models/match.py \
  backend/app/routes/actualites.py \
  backend/app/routes/matchs.py \
  backend/app/routes/public.py \
  backend/app/routes/sport_engine.py \
  backend/app/schemas/match.py \
  backend/app/services/recalcul_stats.py \
  backend/app/services/timeline.py \
  backend/tests/test_annulation_match.py \
  frontend-web/src/api.js \
  frontend-web/src/pages/OrgaMatch.jsx \
  frontend-web/src/pages/orga/saison.js \
  docs/PROCEDURE_ANNULATION_INFO-2026.md

git diff --cached --check
git commit -m "feat: annulation reversible des matchs"
git push origin main
```

Ces trois dernières commandes restent à exécuter manuellement.
