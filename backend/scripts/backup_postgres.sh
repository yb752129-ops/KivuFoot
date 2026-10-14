#!/usr/bin/env bash
set -euo pipefail

# Backup non destructif. Ce script ne se connecte jamais a la production
# sans que DATABASE_URL soit fourni explicitement par l'operateur.
: "${DATABASE_URL:?Definir DATABASE_URL via le secret manager}"

BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="${BACKUP_DIR}/kivufoot-${STAMP}.dump"
TEMP="${TARGET}.part"

mkdir -p "${BACKUP_DIR}"
trap 'rm -f "${TEMP}"' EXIT

pg_dump \
  --dbname="${DATABASE_URL}" \
  --format=custom \
  --no-owner \
  --no-acl \
  --file="${TEMP}"

# Verification locale: le fichier doit etre lisible par pg_restore avant archivage.
pg_restore --list "${TEMP}" >/dev/null
mv "${TEMP}" "${TARGET}"
sha256sum "${TARGET}" > "${TARGET}.sha256"

# La retention est locale a ce repertoire. L'archivage hors site doit etre
# configure separement avec un stockage chiffre et une politique validee.
find "${BACKUP_DIR}" -type f -name 'kivufoot-*.dump' -mtime "+${RETENTION_DAYS}" -delete
find "${BACKUP_DIR}" -type f -name 'kivufoot-*.dump.sha256' -mtime "+${RETENTION_DAYS}" -delete

echo "Backup cree: ${TARGET}"
