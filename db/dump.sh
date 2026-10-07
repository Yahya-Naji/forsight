#!/usr/bin/env bash
# Snapshot the Supabase Postgres (public schema) into db/dumps/<UTC stamp>/.
#
#   schema.sql   DDL only — tables, views, functions, policies
#   data.sql     INSERTs, one per row, readable and diffable
#   full.dump    custom format for pg_restore (schema + data)
#
# No local Postgres needed: pg_dump runs from the postgres:17 image, which can
# read any server at or below 17. The connection string comes from .env and is
# passed through the environment, never on the command line.
#
# Dumps are gitignored: the graph holds text from Restricted client material.
#
#   ./db/dump.sh                 # or: make dump
#   pg_restore -d "$URL" --no-owner --clean db/dumps/<stamp>/full.dump
set -euo pipefail
cd "$(dirname "$0")/.."

URL=$(grep -E '^SUPABASE_DB_URL=' .env | head -1 | cut -d= -f2- | tr -d '"' | sed 's/[[:space:]]*#.*$//')
[ -n "$URL" ] || { echo "SUPABASE_DB_URL is not set in .env" >&2; exit 1; }

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="db/dumps/$STAMP"
mkdir -p "$OUT"

pgdump() {
  docker run --rm -e DBURL="$URL" -v "$PWD/$OUT:/out" postgres:17 \
    sh -c "pg_dump \"\$DBURL\" --schema=public --no-owner --no-privileges $*"
}

echo "→ schema"; pgdump --schema-only -f /out/schema.sql
echo "→ data";   pgdump --data-only --inserts --rows-per-insert=1 -f /out/data.sql
echo "→ full";   pgdump -Fc -f /out/full.dump

ln -sfn "$STAMP" db/dumps/latest
du -sh "$OUT"/*
echo "✅ $OUT"
