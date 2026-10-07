#!/usr/bin/env bash
# Restore a snapshot from db/dumps/ into any Postgres — a local one to inspect
# the graph offline, or a fresh Supabase project.
#
# Supabase keeps pgcrypto/uuid-ossp in an `extensions` schema and grants RLS
# policies to anon/authenticated/service_role; a plain Postgres has neither, so
# both are created first (idempotently) or six tables fail to restore.
#
#   ./db/restore.sh "postgresql://postgres:x@host.docker.internal:5432/postgres"
#   ./db/restore.sh "$URL" db/dumps/20260930T113432Z
#
# Local throwaway database:
#   docker run -d --name foresight-db -p 5432:5432 -e POSTGRES_PASSWORD=x postgres:17
#
# pg_restore runs inside a container, so a database on this machine is reached
# as host.docker.internal, not localhost.
set -euo pipefail
cd "$(dirname "$0")/.."

TARGET=${1:?usage: db/restore.sh <postgres-url> [dump-dir]}
DIR=${2:-db/dumps/latest}
DIR=$(cd "$DIR" && pwd -P)

docker run --rm -i --network host -e DBURL="$TARGET" -v "$DIR:/in:ro" postgres:17 sh -c '
psql "$DBURL" -v ON_ERROR_STOP=1 -q <<SQL
create schema if not exists extensions;
create extension if not exists pgcrypto schema extensions;
create extension if not exists "uuid-ossp" schema extensions;
do \$\$ begin
  create role anon;          exception when duplicate_object then null; end \$\$;
do \$\$ begin
  create role authenticated; exception when duplicate_object then null; end \$\$;
do \$\$ begin
  create role service_role;  exception when duplicate_object then null; end \$\$;
SQL
pg_restore -d "$DBURL" --no-owner --clean --if-exists /in/full.dump'
echo "✅ restored $(basename "$DIR")"
