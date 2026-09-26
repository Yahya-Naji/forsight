"""Apply supabase/migrations/*.sql in order, against SUPABASE_DB_URL.

Each file runs in its own transaction, so a failure rolls back that file only
and the ones already applied stay applied. Every migration here is written to be
re-runnable (upserts, `if not exists`, `drop policy if exists`).

  python apply_migrations.py            # apply all, in filename order
  python apply_migrations.py --only 005 # apply one
  python apply_migrations.py --check    # connect and list tables, change nothing
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import psycopg
from dotenv import load_dotenv

load_dotenv()
MIGRATIONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "supabase", "migrations")


def connect():
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        sys.exit("SUPABASE_DB_URL is not set.\n"
                 "Supabase dashboard -> Connect -> Session pooler (IPv4-safe), e.g.\n"
                 "  SUPABASE_DB_URL=postgresql://postgres.<ref>:<PASSWORD>@aws-0-<region>"
                 ".pooler.supabase.com:5432/postgres")
    return psycopg.connect(url, connect_timeout=20)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="substring of the migration filename")
    ap.add_argument("--check", action="store_true", help="connect and list tables only")
    a = ap.parse_args()

    with connect() as conn:
        if a.check:
            with conn.cursor() as cur:
                cur.execute("select table_name from information_schema.tables "
                            "where table_schema='public' order by table_name")
                names = [r[0] for r in cur.fetchall()]
            print("connected. %d table(s)/view(s) in public:" % len(names))
            for n in names:
                print("  ·", n)
            return

        files = sorted(glob.glob(os.path.join(MIGRATIONS, "*.sql")))
        if a.only:
            files = [f for f in files if a.only in os.path.basename(f)]
        if not files:
            sys.exit("no migrations matched")

        for path in files:
            name = os.path.basename(path)
            sql = open(path, encoding="utf-8").read()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
                print("✅ %s" % name)
            except Exception as exc:
                conn.rollback()
                print("❌ %s\n   %s" % (name, str(exc).strip().splitlines()[0]))
                sys.exit(1)

        with conn.cursor() as cur:
            cur.execute("select count(*) from source_registry")
            n_sources = cur.fetchone()[0]
            cur.execute("select table_name from information_schema.tables "
                        "where table_schema='public'")
            n_tables = len(cur.fetchall())
        print("\nall migrations applied — %d tables, %d registry sources"
              % (n_tables, n_sources))


if __name__ == "__main__":
    main()
