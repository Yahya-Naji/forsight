"""Shared config: env + Supabase client.

Env is read lazily so the collectors can run with --dry-run (live API calls,
domain mapping, parsing) on a machine that has no Supabase credentials.
Anything that actually touches the database calls db() and fails loudly there.
"""
import datetime as _dt
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")  # service role: pipeline only, never in the web app
# LLM config lives in llm.py — the one place the pipeline talks to a model.


def db():
    missing = [name for name, value in
               (("SUPABASE_URL", SUPABASE_URL), ("SUPABASE_SERVICE_KEY", SUPABASE_KEY))
               if not value]
    if missing:
        raise RuntimeError(
            "missing env var(s): %s — copy .env.example to .env and fill them in, "
            "or pass --dry-run to run a collector without a database."
            % ", ".join(missing))
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# --------------------------------------------------------------------------
# pipeline run tracking
# --------------------------------------------------------------------------
# The console records a requested run as QUEUED; only the pipeline itself may
# report progress. Every stage boundary calls update_run(), so the checklist on
# /generate reflects what actually happened rather than an optimistic guess.
#
# Stage keys are the contract with web/app/generate/page.tsx:
STAGES = ("collect", "gate1", "extract", "gate2", "rules",
          "synthesize", "forecast", "generate", "verify")


def update_run(run_id, stage=None, status=None, counts=None,
               error=None, report_id=None):
    """Advance a pipeline_runs row. Never raises — tracking must not be able
    to break the pipeline it is tracking."""
    if not run_id:
        return
    patch = {}
    if stage:
        if stage not in STAGES:
            raise ValueError("unknown stage %r (expected one of %s)" % (stage, ", ".join(STAGES)))
        patch["stage"] = stage
    if status:
        patch["status"] = status
        if status == "RUNNING":
            patch["started_at"] = "now()"
        if status in ("DONE", "FAILED"):
            patch["finished_at"] = "now()"
    if error:
        patch["error"] = str(error)[:2000]
    if report_id:
        patch["report_id"] = report_id
    if not patch:
        return

    try:
        sb = db()
        if counts:
            existing = (sb.table("pipeline_runs").select("counts")
                        .eq("id", run_id).execute().data)
            merged = dict((existing[0].get("counts") or {}) if existing else {})
            merged.update(counts)
            patch["counts"] = merged
        # Supabase REST has no now(); send an ISO timestamp instead.
        for key in ("started_at", "finished_at"):
            if patch.get(key) == "now()":
                patch[key] = _dt.datetime.now(_dt.timezone.utc).isoformat()
        res = sb.table("pipeline_runs").update(patch).eq("id", run_id).execute()
        if not (res.data or []):
            # An UPDATE matching zero rows returns cleanly, so a wrong run id
            # would otherwise be indistinguishable from a successful report.
            print("  (run tracking: no pipeline_runs row with id %s — "
                  "progress is NOT being recorded)" % run_id)
    except Exception as exc:                      # tracking is best-effort
        print("  (run tracking failed: %s)" % exc)
