"""Fulfil one report request from the console: the client-facing pipeline.

A request is a pipeline_runs row (from /api/generate). Both the GitHub Action
(pipeline.yml) and the local queue worker (runner.py) call this, so the path a
client's report takes is defined once.

What a request runs, and what it deliberately does not:

  rules      re-score against today's evidence (seconds)
  generate   draft every section against the brief, verify each in the loop,
             cut sentences that keep failing, freeze the citations
  verify     the final audit; blocking sentences are cut and logged, then
             re-audited — the report is issued clean or the run fails

Collection, extraction, synthesis and forecasting are NOT re-run per request.
They rebuild shared objects (signals, findings, forecasts) that every report
cites, take tens of minutes, and are the daily job's work (analyse.yml). A
request writes from the graph as it stands, so it returns in minutes.

  python request.py --run-id <uuid>
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

import config
from config import db

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

# Drafting model for client requests. gpt-4o-mini writes sections that pass
# verification at a fraction of the latency of the reasoning deployments.
GEN_DEPLOYMENT = os.environ.get("GEN_DEPLOYMENT", "gpt-4o-mini")
BRIEF_TEMPLATE = os.environ.get("BRIEF_TEMPLATE", "TPL-BRIEF-01")
DEFAULT_TEMPLATE = "TPL-BRIEF-01"

LABEL = {"CYBERSECURITY": "Cybersecurity", "AI": "Artificial Intelligence",
         "ELECTRONIC_WARFARE": "Electronic Warfare", "PROCUREMENT": "Procurement"}


def step(name, args, env=None) -> int:
    print("\n── %s ──" % name, flush=True)
    return subprocess.call([PY, os.path.join(HERE, args[0])] + args[1:], cwd=HERE,
                           env=dict(os.environ, **(env or {})))


def fulfil(run_id: str) -> int:
    sb = db()
    rows = sb.table("pipeline_runs").select("*").eq("id", run_id).execute().data
    if not rows:
        print("run %s not found" % run_id)
        return 2
    run = rows[0]
    pillar, brief = run["pillar"], run.get("brief_id")
    template = BRIEF_TEMPLATE if brief else (run.get("template_id") or DEFAULT_TEMPLATE)
    # The row may carry a note from the queue ("waiting for a runner"); it is
    # stale the moment a runner picks the request up.
    sb.table("pipeline_runs").update({"error": None}).eq("id", run_id).execute()
    config.update_run(run_id, status="RUNNING")
    print("request %s · %s · %s%s" % (run_id[:8], pillar, template,
                                      " · brief %s" % brief[:8] if brief else ""))

    if step("rules", ["rules.py", "--run-id", run_id]) != 0:
        config.update_run(run_id, status="FAILED", error="rules.py failed")
        return 1

    gen = ["generate.py", "--run-id", run_id, "--pillar", pillar,
           "--template", template, "--workers", "7", "--fresh"]
    if brief:
        gen += ["--brief", brief]
    else:
        gen += ["--title", (run.get("title") or "").strip()
                or "%s Strategic Foresight Brief" % LABEL.get(pillar, pillar)]
    if step("generate", gen, env={"AZURE_OPENAI_DEPLOYMENT": GEN_DEPLOYMENT,
                                  "GEN_MAX_OUTPUT": os.environ.get("GEN_MAX_OUTPUT", "16000")}) != 0:
        config.update_run(run_id, status="FAILED", error="generate.py failed — see the log")
        return 1

    # The report this run wrote, by id — never "the newest report", which is
    # whichever of two concurrent requests finished last.
    report_id = (sb.table("pipeline_runs").select("report_id").eq("id", run_id)
                 .execute().data[0].get("report_id"))
    if not report_id:
        config.update_run(run_id, status="FAILED", error="generate.py saved no report")
        return 1

    # verify.py sets DONE or FAILED on the run itself. Exit 1 means blockers
    # survived pruning — an analytical outcome, recorded on the row, not a crash.
    code = step("verify", ["verify.py", "--report", report_id, "--run-id", run_id, "--prune"])
    return 0 if code in (0, 1) else code


def claim_waiting(min_age_minutes: int = 3, max_age_minutes: int = 120):
    """The oldest request nobody picked up: queued for at least `min_age`
    minutes (a dispatched job has started by then, so the sweep never races it)
    and not so old that the person asking has given up."""
    from datetime import datetime, timedelta, timezone
    sb = db()
    now = datetime.now(timezone.utc)
    rows = (sb.table("pipeline_runs").select("id")
            .eq("status", "QUEUED")
            .lt("requested_at", (now - timedelta(minutes=min_age_minutes)).isoformat())
            .gt("requested_at", (now - timedelta(minutes=max_age_minutes)).isoformat())
            .order("requested_at").limit(1).execute().data)
    if not rows:
        return None
    # Conditional on still being QUEUED, so two sweeps cannot take one request.
    got = (sb.table("pipeline_runs").update({"status": "RUNNING"})
           .eq("id", rows[0]["id"]).eq("status", "QUEUED").execute().data)
    return rows[0]["id"] if got else None


def main():
    ap = argparse.ArgumentParser(description="Fulfil one queued report request")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--run-id")
    g.add_argument("--next-waiting", action="store_true",
                   help="claim the oldest request left waiting (the scheduled sweep)")
    a = ap.parse_args()
    if a.next_waiting:
        a.run_id = claim_waiting()
        if not a.run_id:
            print("no request waiting")
            return
    try:
        sys.exit(fulfil(a.run_id))
    except Exception as exc:                                   # noqa: BLE001
        config.update_run(a.run_id, status="FAILED", error=str(exc)[:300])
        raise


if __name__ == "__main__":
    main()
