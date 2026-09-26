"""STEP 2 — Collector CLI. Thin dispatcher over the three collection lanes.

  LANE A  scheduled feeds        rss + scrape registry rows, daily cron
  LANE B  question-driven search GDELT DOC 2.0 + site-scoped Serper
  LANE C  structured APIs        MITRE ATT&CK STIX + NVD, straight to entities

  python collect.py --lane a --pillar CYBERSECURITY --limit 3
  python collect.py --lane b --question-id EW-02
  python collect.py --lane b --query "counter-UAS UAE"
  python collect.py --lane c --loader attack
  python collect.py --emit-sql > ../supabase/migrations/004_source_registry_v2.sql

--dry-run exercises every lane (including live API calls and domain mapping)
without a Supabase connection, which is how the lanes are demoed and tested.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config                                          # noqa: E402
from collectors import lane_a, lane_b, lane_c          # noqa: E402
from collectors.registry import emit_sql               # noqa: E402

PILLARS = ["CYBERSECURITY", "AI", "ELECTRONIC_WARFARE", "PROCUREMENT"]


def main():
    ap = argparse.ArgumentParser(description="Three-lane document collector")
    ap.add_argument("--run-id", help="pipeline_runs row to report progress into")
    ap.add_argument("--lane", choices=["a", "b", "c"],
                    help="a=scheduled feeds  b=question-driven search  c=structured APIs")
    ap.add_argument("--pillar", choices=PILLARS)
    # No global default: "5" means 5 entries per feed in Lane A, but silently
    # capping Lane C at 5 of 36 threat actors is wrong. Each lane applies its own.
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--question-id", help="lane b: derive the query from this question")
    ap.add_argument("--query", help="lane b: ad-hoc query text")
    ap.add_argument("--url", action="append",
                    help="lane a: ingest this specific document (repeatable)")
    ap.add_argument("--depth", type=int, default=0,
                    help="lane a --url: follow policy/PDF links one level deep")
    ap.add_argument("--timespan", default="3months", help="lane b: GDELT window")
    ap.add_argument("--sourcecountry", help="lane b: GDELT country filter, e.g. AE")
    ap.add_argument("--loader", choices=["attack", "nvd"], help="lane c loader")
    ap.add_argument("--days", type=int, default=120,
                    help="lane c nvd: publication window in days (NVD caps at 120)")
    ap.add_argument("--dry-run", action="store_true",
                    help="run the lane without writing to Supabase")
    ap.add_argument("--emit-sql", action="store_true",
                    help="print the generated source_registry migration and exit")
    args = ap.parse_args()
    config.update_run(getattr(args, "run_id", None), stage="collect", status="RUNNING")

    if args.emit_sql:
        print(emit_sql())
        return

    if not args.lane:
        ap.error("--lane is required (or use --emit-sql)")

    sb = None
    if not args.dry_run:
        from config import db
        sb = db()

    if args.lane == "a":
        if args.url:
            lane_a.run_urls(sb, args.url, dry_run=args.dry_run, depth=args.depth)
        elif args.pillar:
            lane_a.run(sb, args.pillar, limit=args.limit or 5, dry_run=args.dry_run)
        else:
            ap.error("lane a requires --pillar or --url")
    elif args.lane == "b":
        lane_b.run(sb, question_id=args.question_id, query=args.query,
                   pillar=args.pillar, limit=args.limit or 10, timespan=args.timespan,
                   sourcecountry=args.sourcecountry, dry_run=args.dry_run)
    else:
        if not args.loader:
            ap.error("lane c requires --loader attack|nvd")
        lane_c.run(sb, args.loader, limit=args.limit, days=args.days,
                   dry_run=args.dry_run)


if __name__ == "__main__":
    main()
