#!/usr/bin/env bash
set -euo pipefail

# Restauration volontairement bloquee par defaut. Toujours tester d'abord
# dans une base isolee; aucune restauration de production ne doit etre faite
# sans autorisation distincte et validation de l'operateur.
: "${DATABASE_URL:?Definir DATABASE_URL vers une base de restauration}"
: "${BACKUP_FILE:?Definir BACKUP_FILE vers un dump .dump}"

if [[ "${ALLOW_DESTRUCTIVE_RESTORE:-NO}" != "YES" ]]; then
  echo "Refus: definir ALLOW_DESTRUCTIVE_RESTORE=YES apres validation du plan." >&2
  exit 2
fi

[[ -f "${BACKUP_FILE}" ]] || { echo "Dump introuvable: ${BACKUP_FILE}" >&2; exit 1; }
if [[ -f "${BACKUP_FILE}.sha256" ]]; then
  sha256sum --check "${BACKUP_FILE}.sha256"
fi

pg_restore \
  --dbname="${DATABASE_URL}" \
  --format=custom \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --exit-on-error \
  "${BACKUP_FILE}"

echo "Restauration terminee dans la base cible indiquee par DATABASE_URL."
