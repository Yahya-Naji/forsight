"""Write every agent's prompt to agents/prompts/, one file per agent.

The prompts stay where they run — as constants beside the code that fills them —
so this reads them out rather than moving them. Python constants come out of the
AST (nothing is imported, so no keys or database are needed for that part);
the three console prompts come out of their route files; the per-section drafting
instructions live in Postgres and are read from report_templates.

Each file carries the facts a reviewer needs to judge the prompt: which team owns
it, which deployment and effort it runs at, what schema its output must parse
into, and what the symbolic layer does to that output afterwards.

  python export_prompts.py              # write agents/prompts/
  python export_prompts.py --check      # exit 1 if the files have drifted
  python export_prompts.py --no-db      # skip the section instructions
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "agents", "prompts")

# team, agent, source, symbol(s), tier, effort, output, after
AGENTS: List[dict] = [
    dict(team="intake", agent="brief-interviewer",
         source="web/app/api/brief/route.ts", ts=r"const SYSTEM = `([\s\S]*?)`;",
         tier="strong", effort="default", output="prose + <<<BRIEF>>> JSON block",
         after="Route parses the BRIEF block into report_briefs; focus_terms scope which evidence reaches the drafter."),
    dict(team="extraction", agent="evidence-extractor",
         source="pipeline/extract.py", symbols=["PROMPT"],
         tier="fast", effort="medium", output="models.ExtractionResult",
         after="Pillar/topic rule rejects strays; layers.resolve_env_layer overrides UAE claims the quote does not support; schema failures go to research_gaps."),
    dict(team="extraction", agent="evidence-refiler",
         source="pipeline/refile.py", symbols=["PROMPT"],
         tier="strong", effort="medium", output="refile.PlacementBatch",
         after="Code drops any placement whose ew_hook is not verbatim in the claim (REVIEW); the pillar follows the topic; nothing changes until a reviewed CSV is applied."),
    dict(team="extraction", agent="figure-classifier",
         source="pipeline/figures.py", symbols=["CLASSIFY_PROMPT"],
         tier="fast", effort="low", output="figures.FigureBatch",
         after="The model proposes a kind and description; rules.figure_is_informative decides what is kept."),
    dict(team="validation", agent="gate3-corroboration-merge",
         source="pipeline/decisions.py", symbols=["PROMPT"],
         tier="strong", effort="high", output="decisions.MergeBatch",
         after="Merge only at p>=0.85; owned by the Jev decision layer."),
    dict(team="validation", agent="gate4-forecast-support",
         source="pipeline/decisions.py", symbols=["GATE4_PROMPT"],
         tier="strong", effort="high", output="decisions.SupportBatch",
         after="A forecast is admitted only at p>=0.70 (FORECAST_SUPPORT_THRESHOLD); owned by the Jev decision layer."),
    dict(team="validation", agent="citation-entailment",
         source="pipeline/verify.py", symbols=["ENTAIL_PROMPT"],
         tier="fast|strong", effort="high", output="verify.EntailmentBatch",
         after="Runs after the four deterministic checks (citation, unsourced, class, gate); a failed item becomes a violation and blocks release."),
    dict(team="analysis", agent="synthesiser",
         source="pipeline/synthesize.py", symbols=["PROMPT"],
         tier="strong", effort="high", output="models.Synthesis",
         after="corroboration_admission needs >=2 distinct real evidence rows; strength and risk likelihood/impact are computed, never taken from the model."),
    dict(team="analysis", agent="forecaster",
         source="pipeline/forecast.py", symbols=["PROMPT", "GATE_NOTE"],
         tier="strong", effort="high", output="forecast.ForecastSet",
         after="forecast_calibration computes the plausibility band from publisher independence; GATE_NOTE is appended only while the UAE gate is open."),
    dict(team="analysis", agent="strategist",
         source="pipeline/strategize.py", symbols=["PROMPT"],
         tier="strong", effort="high", output="strategize proposal schema",
         after="opportunity_scoring and cross_impact_severity are computed by rule."),
    dict(team="drafting", agent="section-drafter",
         source="pipeline/generate.py", symbols=["SECTION_PROMPT", "RETRY_SUFFIX"],
         tier="strong", effort="high", output="markdown",
         after="verify.check_section + opener/density/structure checks; failures are fed back through RETRY_SUFFIX up to max_retries, then the section is withheld and named."),
    dict(team="reader", agent="report-chat",
         source="web/app/api/report/chat/route.ts", ts=r"const system = `([\s\S]*?)`;",
         tier="strong", effort="default", output="prose + optional <<<REWRITE>>> block",
         after="A proposed rewrite lands in report_edits and must be applied explicitly."),
    dict(team="reader", agent="evidence-ask",
         source="web/app/api/ask/route.ts", ts=r"content: `([\s\S]*?)`,",
         tier="anthropic (LLM_MODEL)", effort="default", output="prose",
         after="Evidence rows are returned alongside the answer so every citation is checkable."),
    dict(team="evaluation", agent="benchmark-extractor",
         source="pipeline/evaluate.py", symbols=["EXTRACT_PROMPT"],
         tier="fast", effort="medium", output="evaluate.BenchRegisters",
         after="Registers pulled from the human benchmark feed recall scoring."),
    dict(team="evaluation", agent="benchmark-matcher",
         source="pipeline/evaluate.py", symbols=["MATCH_PROMPT"],
         tier="strong", effort="high", output="evaluate.MatchSet",
         after="Matches become recall/precision in the scorecard."),
]


def _py_constant(path: str, name: str) -> str:
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError("%s not found in %s" % (name, path))


def _ts_literal(path: str, pattern: str) -> str:
    m = re.search(pattern, open(path, encoding="utf-8").read())
    if not m:
        raise KeyError("pattern %r not found in %s" % (pattern, path))
    return m.group(1)


def _render(a: dict) -> str:
    path = os.path.join(ROOT, a["source"])
    head = ["---",
            "agent: %s" % a["agent"],
            "team: %s" % a["team"],
            "source: %s" % a["source"],
            "deployment: %s" % a["tier"],
            "effort: %s" % a["effort"],
            "output: %s" % a["output"],
            "---", "",
            "# %s" % a["agent"], "",
            "**After the model answers:** %s" % a["after"], "",
            "Placeholders in `{braces}` (Python) or `${...}` (TypeScript) are filled "
            "at run time. Generated by `pipeline/export_prompts.py` — edit the "
            "source file, not this one.", ""]
    if "ts" in a:
        head += ["## Prompt", "", "```text", _ts_literal(path, a["ts"]).strip("\n"), "```", ""]
    else:
        for sym in a["symbols"]:
            head += ["## `%s`" % sym, "", "```text",
                     _py_constant(path, sym).strip("\n"), "```", ""]
    return "\n".join(head)


def _section_instructions() -> Dict[str, str]:
    """One file per report template: every section's drafting instructions."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import db
    rows = db().table("report_templates").select("id,name,sections").order("id").execute().data
    out = {}
    for r in rows:
        sections = r["sections"]
        if isinstance(sections, str):
            sections = json.loads(sections)
        body = ["---", "agent: section-drafter", "team: drafting",
                "source: report_templates.%s (Postgres)" % r["id"], "---", "",
                "# %s — section instructions" % (r.get("name") or r["id"]), "",
                "Each block is substituted into `{instructions}` of the section-drafter "
                "prompt. Generated from the database by `pipeline/export_prompts.py`.", ""]
        for s in sections:
            body += ["## %s — %s" % (s.get("key", "?"), s.get("title", "")), ""]
            if s.get("inputs"):
                body += ["Inputs: `%s`" % ", ".join(s["inputs"]) if isinstance(s["inputs"], list)
                         else "Inputs: `%s`" % s["inputs"], ""]
            body += [(s.get("instructions") or "_(none)_").strip(), ""]
        out["drafting/templates/%s.md" % r["id"]] = "\n".join(body)
    return out


def _index(files: Dict[str, str]) -> str:
    lines = ["# Agent prompts", "",
             "Every prompt the system sends to a model, grouped by team. Generated by "
             "`make prompts`; `make prompts-check` fails if a source prompt changed "
             "without regenerating. See `../TEAMS.md` for how the teams hand off.", "",
             "| Team | Agent | Deployment | Effort | Output | Source |",
             "|---|---|---|---|---|---|"]
    for a in AGENTS:
        lines.append("| %s | [%s](%s/%s.md) | %s | %s | `%s` | `%s` |" % (
            a["team"], a["agent"], a["team"], a["agent"], a["tier"], a["effort"],
            a["output"], a["source"]))
    tpl = sorted(k for k in files if k.startswith("drafting/templates/"))
    if tpl:
        lines += ["", "Section instructions (from `report_templates`):", ""]
        lines += ["- [%s](%s)" % (os.path.basename(k)[:-3], k) for k in tpl]
    return "\n".join(lines) + "\n"


def build(with_db: bool) -> Dict[str, str]:
    files = {"%s/%s.md" % (a["team"], a["agent"]): _render(a) for a in AGENTS}
    if with_db:
        try:
            files.update(_section_instructions())
        except Exception as exc:
            print("section instructions skipped: %s" % exc, file=sys.stderr)
    files["README.md"] = _index(files)
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-db", action="store_true")
    a = ap.parse_args()
    files = build(with_db=not a.no_db)

    if a.check:
        stale = []
        for rel, body in files.items():
            p = os.path.join(OUT, rel)
            if not os.path.exists(p) or open(p, encoding="utf-8").read() != body:
                stale.append(rel)
        for rel in stale:
            print("drifted: agents/prompts/%s" % rel)
        if stale:
            print("run `make prompts` to regenerate")
        return 1 if stale else 0

    for rel, body in files.items():
        p = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
    print("wrote %d file(s) to agents/prompts/" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
