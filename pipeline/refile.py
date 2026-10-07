"""Re-file evidence onto the EW-core topics (migration 025).

Two steps, so nothing is moved or archived before a person has read the list:

  python refile.py                      # propose: writes out/refile/refile-<stamp>.csv + .md
  python refile.py --apply <file.csv>   # apply the reviewed file

The model only proposes a topic from the live list, or NONE. Everything else is
code: the pillar follows the topic, and the action (keep / refile / archive) is
derived by comparing with what the row has today. Edit the `new_topic` or
`action` column of the CSV before applying to overrule any proposal.

Archiving sets evidence.archived_at; the row, its sources and its links stay,
and every pipeline and console read skips it. Clearing archived_at revives it.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import sys
from collections import Counter
from typing import List

from pydantic import BaseModel

import llm
from config import db

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "refile")
BATCH = 20
FIELDS = ["evidence_id", "action", "old_pillar", "old_topic", "new_pillar",
          "new_topic", "new_topic_name", "ew_hook", "reason", "claim"]

PROMPT = """You are filing evidence for a strategic-foresight system whose core
pillar is ELECTRONIC WARFARE (EW). Cybersecurity, AI and Procurement topics exist
only for their impact on EW. Each topic below names the EW functions it affects.

For each evidence row, choose the ONE topic the claim itself bears on, or NONE.

Rules:
- Choose a topic only if the claim, read on its own, says something about that
  topic's EW functions: the spectrum, jamming, spoofing, sensing, emitters,
  navigation warfare, counter-UAS, or the cyber, AI or acquisition questions
  the topic's "EW impact" line describes.
- Generic IT security (malware, ransomware, identity, cloud, phishing), general
  AI policy or industry news, and procurement news with no EW or counter-UAS
  content are NONE. Do not stretch a claim to fit.
- A claim about the drone or loitering-munition threat itself (range, size,
  payload, speed, numbers, control method, new designs) belongs to EW-T19.
  Other counter-UAS claims belong to an EW topic unless they are specifically
  about AI, cyber or acquisition.
- ew_hook: when you choose a topic, copy VERBATIM the words of the claim that
  touch the topic's EW functions (a drone, jamming, a radar, a waveform, RF, a
  counter-UAS system...). A country, a company, "AI", "cyber" or "defence" on
  its own is not a hook. If you cannot copy such words, the answer is NONE and
  ew_hook is empty. A hook that is not in the claim is rejected.
- reason: one short sentence on how the claim bears on the topic.
- Return every evidence_id you were given, exactly once.

Topics:
{topics}

Evidence:
{evidence}
"""


class Placement(BaseModel):
    evidence_id: str
    topic_id: str          # a live topic id, or NONE
    ew_hook: str           # verbatim words of the claim; checked in code
    reason: str


class PlacementBatch(BaseModel):
    items: List[Placement]


def _topics(sb):
    rows = (sb.table("topics")
            .select("id,pillar,name,description,ew_functions,ew_impact")
            .is_("retired_at", "null").order("id").execute().data)
    if not rows:
        sys.exit("no live topics — apply migration 025 first")
    return {r["id"]: r for r in rows}


def _render_topics(topics) -> str:
    out = []
    for t in topics.values():
        line = "%s [%s] %s — %s EW functions: %s." % (
            t["id"], t["pillar"], t["name"], t.get("description") or "",
            ", ".join(t["ew_functions"]))
        if t.get("ew_impact"):
            line += " EW impact: %s" % t["ew_impact"]
        out.append(line)
    return "\n".join(out)


def _hook_in_claim(hook: str, claim: str) -> bool:
    norm = lambda x: " ".join(x.lower().replace("\u2019", "'").split())
    hook = norm(hook).strip(" .,'\"")
    return len(hook) >= 3 and hook in norm(claim)


def propose(sb) -> str:
    topics = _topics(sb)
    rendered = _render_topics(topics)
    rows = (sb.table("evidence").select("id,claim,pillar,topic_id")
            .is_("archived_at", "null").order("id").execute().data)
    print("proposing placements for %d evidence rows against %d topics"
          % (len(rows), len(topics)))

    def ask(chunk):
        ev = "\n".join("%s: %s" % (r["id"], r["claim"]) for r in chunk)
        got = llm.structured(PROMPT.format(topics=rendered, evidence=ev),
                             PlacementBatch, effort="medium",
                             max_output_tokens=12000)
        return {p.evidence_id: p for p in got.items
                if p.topic_id.strip() == "NONE" or p.topic_id.strip() in topics}

    placed = {}
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        placed.update(ask(chunk))
        # A batch can come back short or name a non-topic; ask once more for
        # just those rows before leaving them for a person to decide.
        missing = [r for r in chunk if r["id"] not in placed]
        if missing:
            placed.update(ask(missing))
        print("  %d/%d" % (min(i + BATCH, len(rows)), len(rows)))

    out_rows = []
    for r in rows:
        p = placed.get(r["id"])
        tid = (p.topic_id.strip() if p else "")
        if not p:
            # Skipped twice, or named a topic that does not exist both times.
            action, tid, reason = "REVIEW", "", "no valid proposal after a retry"
        elif tid == "NONE":
            action, reason = "archive", p.reason
        elif not _hook_in_claim(p.ew_hook, r["claim"]):
            # The model named a topic but could not point at the words that put
            # the claim there. That is a stretch, so a person decides.
            action, reason = "REVIEW", "hook %r is not in the claim — %s" % (p.ew_hook, p.reason)
        else:
            action = "keep" if tid == r["topic_id"] else "refile"
            reason = p.reason
        t = topics.get(tid, {})
        out_rows.append({
            "evidence_id": r["id"], "action": action,
            "old_pillar": r["pillar"], "old_topic": r["topic_id"] or "",
            "new_pillar": t.get("pillar", ""), "new_topic": tid if t else "",
            "new_topic_name": t.get("name", ""), "reason": reason,
            "ew_hook": p.ew_hook if p else "",
            "claim": r["claim"],
        })

    os.makedirs(OUT, exist_ok=True)
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(OUT, "refile-%s.csv" % stamp)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out_rows)
    _summary(out_rows, topics, path.replace(".csv", ".md"))
    print("wrote %s" % path)
    print("wrote %s" % path.replace(".csv", ".md"))
    return path


def _summary(rows, topics, path):
    acts = Counter(r["action"] for r in rows)
    lines = ["# Evidence re-filing proposal", "",
             "%d rows: %s." % (len(rows), ", ".join(
                 "%d %s" % (acts[a], a) for a in ("keep", "refile", "archive", "REVIEW") if acts[a])),
             "", "Nothing has changed yet. Edit the CSV's `action` / `new_topic` "
             "columns to overrule, then run `refile.py --apply <csv>`.", "",
             "## Evidence per topic after applying", "",
             "| topic | pillar | name | rows |", "|---|---|---|---|"]
    per = Counter(r["new_topic"] for r in rows if r["action"] in ("keep", "refile"))
    for tid, t in topics.items():
        lines.append("| %s | %s | %s | %d |" % (tid, t["pillar"], t["name"], per[tid]))
    lines += ["", "## Archived, by old pillar", ""]
    for pillar, n in Counter(r["old_pillar"] for r in rows if r["action"] == "archive").most_common():
        lines.append("- %s: %d" % (pillar, n))
    for title, act in (("Re-filed", "refile"), ("Archived", "archive"), ("Needs review", "REVIEW")):
        sel = [r for r in rows if r["action"] == act]
        if not sel:
            continue
        lines += ["", "## %s (%d)" % (title, len(sel)), "",
                  "| evidence | from | to | claim | why |", "|---|---|---|---|---|"]
        for r in sel:
            lines.append("| %s | %s | %s | %s | %s |" % (
                r["evidence_id"], r["old_topic"], r["new_topic"] or "—",
                r["claim"].replace("|", "/")[:140], r["reason"].replace("|", "/")))
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def apply(sb, path: str) -> None:
    topics = _topics(sb)
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    now = dt.datetime.utcnow().isoformat() + "Z"
    done = Counter()
    for r in rows:
        act, eid = r["action"].strip(), r["evidence_id"]
        if act == "refile":
            t = topics.get(r["new_topic"].strip())
            if not t:
                print("  skip %s: %r is not a live topic" % (eid, r["new_topic"]))
                done["skipped"] += 1
                continue
            # The pillar follows the topic; the model never set it.
            sb.table("evidence").update({"topic_id": t["id"], "pillar": t["pillar"]}) \
              .eq("id", eid).execute()
        elif act == "archive":
            sb.table("evidence").update({
                "archived_at": now,
                "archived_reason": "025 EW core: no EW link — %s" % r["reason"],
            }).eq("id", eid).execute()
        elif act != "keep":
            done["skipped"] += 1
            continue
        done[act] += 1
    print("applied %s: %s" % (os.path.basename(path), dict(done)))
    print("next: re-run synthesize / forecast per pillar so signals follow the moved evidence")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", metavar="CSV", help="apply a reviewed proposal file")
    a = ap.parse_args()
    sb = db()
    if a.apply:
        apply(sb, a.apply)
    else:
        propose(sb)


if __name__ == "__main__":
    main()
