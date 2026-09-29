"""Execute queued runs locally, so the console's Run button actually runs.

/api/generate inserts a pipeline_runs row with status QUEUED and then dispatches
to GitHub Actions — but only when GH_TOKEN and GH_REPO are set. Without them the
row stays QUEUED forever, which is the honest state (the console must never
claim a run happened that did not) and a useless demo: the button appears to do
nothing.

This closes the loop on a laptop. It polls for QUEUED rows and runs the pipeline
against them, letting generate.py report its own progress through
config.update_run(), which is what the Engine and Generate screens already read.
Click the button, watch the stages light up.

Nothing here decides anything about content — it is a queue worker. If the
pipeline fails, the row is marked FAILED with the reason, because a run that
died must not read as one that never started.

  python runner.py                 # poll forever
  python runner.py --once          # take one queued run and exit
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import os
from datetime import datetime, timedelta, timezone

import config
from config import db

HERE = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable
DEFAULT_TEMPLATE = "TPL-FETC-23"

PILLAR_LABEL = {"CYBERSECURITY": "Cybersecurity", "AI": "Artificial Intelligence",
                "ELECTRONIC_WARFARE": "Electronic Warfare", "PROCUREMENT": "Procurement"}


def claim(sb, stale_minutes: int = 60):
    """Oldest queued run, ignoring stale ones.

    Oldest-first is the right queue order, but a row left QUEUED from a previous
    session would be claimed ahead of the one somebody just clicked — so a live
    demo runs last week's request and the screen shows the wrong title. Anything
    queued longer ago than `stale_minutes` is abandoned with a reason rather
    than silently jumping the queue.

    Marked RUNNING immediately so two runners cannot take the same row; a laptop
    will only have one, but a race that corrupts a live screen is not worth the
    saved line.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
    stale = (sb.table("pipeline_runs").select("id,requested_at")
             .eq("status", "QUEUED").lt("requested_at", cutoff.isoformat())
             .execute().data)
    for row in stale:
        sb.table("pipeline_runs").update(
            {"status": "FAILED", "finished_at": "now()",
             "error": "abandoned — queued over %d minutes before a runner was "
                      "available" % stale_minutes}).eq("id", row["id"]).execute()
        print("  abandoned stale run %s" % row["id"][:8])

    rows = (sb.table("pipeline_runs")
            .select("id,pillar,title,template_id,status")
            .eq("status", "QUEUED").order("requested_at").limit(1).execute().data)
    if not rows:
        return None
    run = rows[0]
    sb.table("pipeline_runs").update({"status": "RUNNING", "started_at": "now()"}) \
      .eq("id", run["id"]).eq("status", "QUEUED").execute()
    return run


def execute(run) -> int:
    cmd = [PYTHON, os.path.join(HERE, "generate.py"),
           "--run-id", run["id"],
           "--pillar", run["pillar"],
           "--template", run.get("template_id") or DEFAULT_TEMPLATE,
           "--workers", "3", "--retries", "4"]
    # generate.py requires a title unless a brief supplies one, and a row queued
    # from the console may carry none. Failing on argparse would surface as
    # "exited 2" on screen, which tells the viewer nothing.
    title = (run.get("title") or "").strip() or \
        "%s Strategic Foresight Brief" % PILLAR_LABEL.get(run["pillar"], run["pillar"])
    cmd += ["--title", title]

    print("\n▶ run %s · %s · %s" % (run["id"][:8], run["pillar"],
                                    run.get("template_id") or DEFAULT_TEMPLATE))
    # Streamed, not captured: the terminal is half the demo — the retries and
    # refusals scrolling past are the part worth watching.
    return subprocess.call(cmd, cwd=HERE)


HEARTBEAT = os.path.join(os.path.dirname(HERE), "out", ".runner-alive")


def beat():
    """Touch a file the console can stat.

    A queued row that never moves looks identical whether the runner is dead or
    merely busy, and "Queued" forever is the worst thing this console can show —
    it is the one state that tells the viewer nothing. The console reads this
    file's age to say which it is.
    """
    try:
        os.makedirs(os.path.dirname(HEARTBEAT), exist_ok=True)
        with open(HEARTBEAT, "w") as fh:
            fh.write(str(time.time()))
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="take one queued run and exit")
    ap.add_argument("--interval", type=float, default=3.0, help="seconds between polls")
    a = ap.parse_args()
    sb = db()

    print("runner ready — polling for queued runs every %.0fs (ctrl-c to stop)" % a.interval)
    while True:
        beat()
        run = claim(sb)
        if run is None:
            if a.once:
                print("nothing queued.")
                return
            time.sleep(a.interval)
            continue

        beat()
        try:
            code = execute(run)
        except Exception as exc:                       # noqa: BLE001
            code, exc_text = 1, str(exc)[:300]
            config.update_run(run["id"], status="FAILED", error=exc_text)
            print("✗ run %s failed: %s" % (run["id"][:8], exc_text))
        else:
            if code == 0:
                # generate.py sets report_id and the final counts itself; only
                # the terminal state is the runner's to write.
                config.update_run(run["id"], status="DONE")
                print("✓ run %s done" % run["id"][:8])
            else:
                config.update_run(run["id"], status="FAILED",
                                  error="generate.py exited %d" % code)
                print("✗ run %s exited %d" % (run["id"][:8], code))

        if a.once:
            return


if __name__ == "__main__":
    main()
