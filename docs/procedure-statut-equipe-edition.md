# Statut d’équipe dans une édition — procédure contrôlée

Le patch ajoute la migration `0026_statut_equipe_edition` après `0025_match_annulation`.
La migration est structurelle : elle crée les colonnes et donne `actif` par défaut aux inscriptions existantes. Elle n’applique **aucune décision métier**, ne supprime aucune ligne et ne modifie aucun match.

## Origine du jeu synthétique de capture

Le titre « Championnat pilote » visible sur la capture précédente provenait d’un jeu de données synthétiques local, et non de la vraie base : le script Playwright temporaire `/tmp/capture-kivu-status.cjs` interceptait les requêtes API du navigateur et répondait avec des JSON en mémoire (compétition, édition, équipes et quatre statuts simulés). Il n’a exécuté aucun `POST`, `PATCH`, migration ou écriture SQL. Les places des captures ne prouvent donc rien sur le classement réel.

Les captures précédentes sont des artefacts visuels hors production. Le patch correctif livré séparément ne contient ni ces images, ni ce jeu JSON, ni fichier de démonstration ; aucun jeu synthétique n’est ajouté à la base de production.

## Termux : patch unique, commit ciblé (10 commandes)

Avant toute migration, sauvegarder aussi la base PostgreSQL via Render : le bundle Git ci-dessous ne contient **pas** la base. Télécharger `kivufoot-statut-equipe-final.patch` dans `$HOME`, puis utiliser le clone réel à jour. Vérifier que `git status --short` n’affiche aucune modification suivie ou indexée et que `git rev-parse HEAD` affiche `03d63168a500c98f5ed14b6484e9e24a1d144ef2` ; arrêter si ce n’est pas le cas. Les lignes non suivies `?? backups/` et `?? kivufoot-correctifs.patch` peuvent rester, mais ne doivent jamais être ajoutées au commit. Ne jamais utiliser `git add .`.

```sh
cd ~/KivuFoot
pkg install jq
git bundle create "$HOME/kivufoot-avant-statut.bundle" --all
git status --short && git rev-parse HEAD
git apply --check "$HOME/kivufoot-statut-equipe-final.patch"
git apply --index "$HOME/kivufoot-statut-equipe-final.patch"
(cd frontend-web && npm ci && npm run build)
git commit -m "Statut d'équipe par édition"
git push
git status --short && git log -1 --oneline
```

`git apply --index` applique et prépare **uniquement** les fichiers du patch pour le commit. Après le push, vérifier sur Render le redéploiement du même commit et la version Alembic `0026_statut_equipe_edition` avant la moindre décision dans l’admin. Si la migration n’est pas lancée par la configuration Render, utiliser la commande ci-dessous par l’administrateur après sauvegarde de la base.

## Application de la migration — commande restant à exécuter par l’administrateur

Après revue du patch :

```sh
cd ~/KivuFoot/backend
alembic upgrade 0026_statut_equipe_edition
alembic current
```

La commande de statut attendue devient `0026_statut_equipe_edition (head)`.
Aucun statut d’équipe n’est appliqué par cette migration.

## Application manuelle des décisions métier — admin uniquement

À exécuter seulement après le déploiement de la version qui contient l’API, avec l’ID réel de l’édition et un jeton admin. Les requêtes sont auditées et réversibles ; le motif reste privé.

Commencer par résoudre les IDs depuis la réponse publique, sans modifier aucune donnée :

```sh
API='https://kivufoot.onrender.com/api/v1'
SAISON_ID='<ID_EDITION>'
TOKEN='<JETON_ADMIN>'

curl -sS "$API/saisons/$SAISON_ID/clubs" \
  | jq -r '.[] | "club_id=\(.club_id // .id) nom=\(.nom) statut=\(.statut)"'
# relever les IDs de INFO-2026, NUTRITION + OPHTALMOLOGIE, BAE et DROIT
```

### État de référence avant les quatre décisions

Exécuter ces commandes avant le premier `PATCH`, avec `API`, `SAISON_ID` et `TOKEN` définis ci-dessus ; elles enregistrent la référence de la vraie édition :

```sh
mkdir -p $HOME/kivufoot-reference
curl -sS "$API/saisons/$SAISON_ID/clubs/gestion" \
  -H "Authorization: Bearer $TOKEN" \
  > $HOME/kivufoot-reference/clubs-15-avant.json
curl -sS "$API/classement?saison_id=$SAISON_ID" \
  > $HOME/kivufoot-reference/classement-avant.json
for G in A B C D; do
  curl -sS "$API/classement?saison_id=$SAISON_ID&groupe=$G" \
    > "$HOME/kivufoot-reference/groupe-$G-avant.json"
done
jq 'length' $HOME/kivufoot-reference/clubs-15-avant.json
# attendu : 16 inscriptions avant le retrait (INFO-2026 compris)
jq 'length' $HOME/kivufoot-reference/classement-avant.json
# attendu : 16 lignes publiques avant le retrait
jq -r '.[] | .club_nom' $HOME/kivufoot-reference/classement-avant.json | nl -ba
# noter le rang initial de G.G.T-2025 et les places 1 à 11 ;
# si la liste réelle ne correspond pas à 16 inscriptions, STOP avant tout PATCH
```

Vérifier d’abord que les 16 inscriptions sont présentes (les 15 équipes qui resteront publiques **plus** `INFO-2026`) et que les quatre clubs portent leurs noms exacts. Si ce n’est pas le cas, s’arrêter. Ensuite, remplacer les quatre placeholders ci-dessous par les IDs relevés ; exécuter les quatre décisions **une par une** en vérifiant la réponse et le nom avant de passer à la suivante :

```sh
curl -sS -X PATCH "$API/saisons/$SAISON_ID/clubs/<CLUB_INFO_2026>/statut" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"statut":"retire","motif":"INFO-2026 — décision de l’organisation"}'

curl -sS -X PATCH "$API/saisons/$SAISON_ID/clubs/<CLUB_NUTRITION_OPHTALMOLOGIE>/statut" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"statut":"disqualifie","motif":"NUTRITION + OPHTALMOLOGIE — décision de l’organisation"}'

curl -sS -X PATCH "$API/saisons/$SAISON_ID/clubs/<CLUB_BAE>/statut" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"statut":"elimine","motif":"BAE — décision de l’organisation"}'

curl -sS -X PATCH "$API/saisons/$SAISON_ID/clubs/<CLUB_DROIT>/statut" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"statut":"elimine","motif":"DROIT — décision de l’organisation"}'
```

### Même opération depuis l’interface admin/organisateur

1. Se connecter avec un compte `admin` ou `organisateur` autorisé sur la compétition.
2. Ouvrir **Organisation → Équipes** et sélectionner l’édition concernée.
3. Vérifier les 16 inscriptions avant toute décision, dont `INFO-2026` ; relever le classement et les groupes A–D avant modification.
4. Appliquer **Retirer de l’édition** à `INFO-2026`, **Disqualifier** à `NUTRITION + OPHTALMOLOGIE`, **Éliminer** à `BAE` puis à `DROIT` ; contrôler le nom affiché avant chaque clic.
5. Saisir le motif privé demandé. Pour **Retirer de l’édition**, confirmer l’avertissement ; aucune ligne ni aucun match n’est supprimé.
6. Utiliser **Rétablir** pour annuler une décision. Le rétablissement efface le motif privé courant de la ligne mais conserve l’audit historique.
7. Contrôler le panneau **Matchs à venir à confirmer**. Ne pas annuler automatiquement ces matchs.
8. Ouvrir **Classement → Général** : attendre **15 équipes visibles**, places 1–11 inchangées, `G.G.T-2025` 12e, `NUTRITION + OPHTALMOLOGIE` 13e (`DISQ.`), `BAE` 14e (`ÉLIM.`), `DROIT` 15e (`ÉLIM.`) ; comparer aussi **Groupes A–D** à la référence. Si ce résultat diffère, ne pas traiter d’autres décisions et relever l’écart.

Ne pas annuler automatiquement les matchs à venir. Les organisateurs les retrouvent pour confirmation via :

```sh
curl -sS "$API/saisons/$SAISON_ID/clubs/matchs-a-venir-statut" \
  -H "Authorization: Bearer $TOKEN"
```

## Vérification en lecture seule

### État après les quatre décisions

```sh
curl -sS "$API/saisons/$SAISON_ID/clubs/gestion" \
  -H "Authorization: Bearer $TOKEN" \
  > $HOME/kivufoot-reference/clubs-15-apres.json
curl -sS "$API/saisons/$SAISON_ID/clubs"
curl -sS "$API/classement?saison_id=$SAISON_ID"
curl -sS "$API/classement?saison_id=$SAISON_ID&groupe=A"
curl -sS "$API/classement?saison_id=$SAISON_ID&groupe=B"
curl -sS "$API/classement?saison_id=$SAISON_ID&groupe=C"
curl -sS "$API/classement?saison_id=$SAISON_ID&groupe=D"
curl -sS "$API/matchs?saison_id=$SAISON_ID&limit=100"
```

Attendus mécaniques :

```sh
jq 'length' $HOME/kivufoot-reference/clubs-15-apres.json
# attendu : 16 inscriptions conservées dans la vue admin
curl -sS "$API/classement?saison_id=$SAISON_ID" > $HOME/kivufoot-reference/classement-apres.json
jq 'length' $HOME/kivufoot-reference/classement-apres.json
# attendu : 15 lignes publiques ; INFO-2026 est retirée de l’affichage
jq -r '.[] | .club_nom' $HOME/kivufoot-reference/classement-apres.json | nl -ba
# attendu : places 1 à 11 inchangées, 12 G.G.T-2025,
# 13 NUTRITION + OPHTALMOLOGIE, 14 BAE, 15 DROIT.
# Ne pas considérer la capture synthétique comme une preuve des rangs réels.
jq -r '.[] | [.nom, .statut] | @tsv' $HOME/kivufoot-reference/clubs-15-apres.json
# attendu : INFO-2026=retire, NUTRITION + OPHTALMOLOGIE=disqualifie,
#           BAE=elimine, DROIT=elimine ; aucune autre équipe touchée
```

Contrôles attendus :

- `INFO-2026` n’apparaît plus dans les clubs publics, le classement, les groupes, les matchs/calendrier ou la recherche ; ses lignes et matchs existent toujours en base.
- `NUTRITION + OPHTALMOLOGIE`, `BAE` et `DROIT` restent visibles avec `Disqualifié`/`Éliminé`, leurs résultats et leurs rangs numériques ; ils forment le bloc après les actifs.
- Aucun motif privé ne figure dans ces réponses publiques.
- Les matchs de `disqualifie`/`elimine` ne sont pas annulés ; les buts, buteurs, statistiques joueurs et matchs déjà `annule` restent inchangés.
- Comparer avant/après les 16 inscriptions de l’édition (admin), leurs noms et leurs statuts : aucune suppression. Le classement public après retrait a **15 équipes** : places 1 à 11 inchangées ; 12 `G.G.T-2025`, 13 `NUTRITION + OPHTALMOLOGIE`, 14 `BAE`, 15 `DROIT`. Signaler tout autre club touché et tout changement constaté dans A–D ; arrêter la procédure si les données réelles divergent.

## Rétablir une décision

```sh
curl -sS -X POST "$API/saisons/$SAISON_ID/clubs/<CLUB_ID>/retablir" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{}'
```

L’action écrit un audit avant/après avec l’utilisateur et la date. Elle ne réécrit ni score, ni événement, ni match.

## Retour arrière

La migration refuse volontairement le downgrade tant qu’une décision non active existe. Après rétablissement contrôlé des équipes et vérification de l’audit :

```sh
cd ~/KivuFoot/backend
alembic downgrade 0025_match_annulation
alembic current
```

Le retour arrière retire seulement les colonnes de statut et leur contrainte ; il ne supprime aucune ligne de club, match, événement, buteur ou statistique.
