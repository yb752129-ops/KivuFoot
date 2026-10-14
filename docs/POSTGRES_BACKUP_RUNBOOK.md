# KivuFoot - sauvegardes PostgreSQL

## Perimetre

Ce runbook prepare des sauvegardes logiques PostgreSQL sans modifier les
 donnees historiques et sans lancer de commande sur la production.

Les scripts sont:

- `backend/scripts/backup_postgres.sh`: `pg_dump` au format custom, verification
  avec `pg_restore --list`, checksum SHA-256 et retention locale;
- `backend/scripts/restore_postgres.sh`: restauration volontairement bloquee
  tant que `ALLOW_DESTRUCTIVE_RESTORE=YES` n'est pas defini.

Les PDF, logos et autres objets Supabase Storage ne sont pas inclus dans un
`pg_dump`. Leur retention et leur restauration doivent etre traitees par la
politique du bucket et un export objet separe.

## Pre-requis

- `pg_dump`, `pg_restore` et `sha256sum` disponibles;
- `DATABASE_URL` fourni par le secret manager, jamais commite;
- un repertoire local ou objet chiffre, avec acces limite;
- une base de restauration isolee pour les exercices.

Exemple local uniquement:

```bash
cd backend
DATABASE_URL='postgresql+asyncpg://user:password@host:5432/database' \
BACKUP_DIR='/var/backups/kivufoot/postgres' \
./scripts/backup_postgres.sh
```

Ne pas copier cet exemple dans un fichier contenant un vrai secret.

## Politique a faire valider

Les valeurs ci-dessous sont des hypotheses operationnelles, pas des faits
confirmes par KivuFoot:

- frequence cible: une sauvegarde quotidienne et une conservation courte des
  dumps recents;
- conservation cible: 30 jours en ligne et une copie hors site chiffree;
- RPO cible: 24 heures au maximum avant validation par l'operateur;
- RTO cible: a mesurer pendant un exercice, sans annoncer de delai avant la
  mesure;
- verification: checksum a chaque dump, puis restauration de test au moins
  une fois par mois si l'organisation valide ce rythme.

Le fournisseur, le bucket, la region, le chiffrement, la retention definitive
et les personnes autorisees restent a confirmer.

## Procedure de restauration de test

1. Creer une base PostgreSQL isolee, jamais la base de production.
2. Recuperer le dump et son fichier `.sha256` depuis le stockage autorise.
3. Verifier le checksum.
4. Lancer le script avec `DATABASE_URL` pointe vers la base isolee et
   `ALLOW_DESTRUCTIVE_RESTORE=YES`.
5. Executer les migrations attendues uniquement si le plan de restauration le
   prevoit; ne pas appliquer une migration destructive automatiquement.
6. Verifier les tables, le nombre de lignes, les index, les routes de sante et
   un echantillon de documents.
7. Mesurer le temps reel et consigner les ecarts.
8. Detruire la base de test selon la procedure de l'operateur, sans toucher aux
   donnees historiques de production.

Exemple de commande de test, apres validation humaine:

```bash
DATABASE_URL='postgresql://restore_user:password@restore-host:5432/kivufoot_restore' \
BACKUP_FILE='/secure-backups/kivufoot-20261014T000000Z.dump' \
ALLOW_DESTRUCTIVE_RESTORE=YES \
./backend/scripts/restore_postgres.sh
```

## Exploitation et controles

- Ne pas mettre `DATABASE_URL`, un mot de passe, une cle Supabase ou un dump
  dans GitHub, dans le depot ou dans une capture d'ecran.
- Une sauvegarde reussie n'est pas une restauration prouvee: conserver le
  compte-rendu de chaque exercice.
- Avant toute operation de production, obtenir une autorisation distincte et
  confirmer la cible, le dump, l'heure et le plan de retour.
- Les scripts ne suppriment aucune donnee de production; le nettoyage de
  retention concerne uniquement `BACKUP_DIR`.
