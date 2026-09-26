"""LANE B — question-driven search. Triggered per strategic question, never on
a schedule: research starts from a strategic question, not from random
information collection (FETC deck, slide 5).

Two providers:
  (a) GDELT DOC 2.0  — free, no key, global news index
  (b) Serper         — site-scoped search over the Tier 1/2 'search' rows

TIER INTEGRITY: GDELT is an aggregator and confers no authority. An article it
returns is stored against ITS OWN publisher's registry row when we know that
publisher; SRC-API-001 is used only when the domain matches nothing.

  python collect.py --lane b --question-id EW-02
  python collect.py --lane b --query "counter-UAS UAE"
"""
from __future__ import annotations

import os
import re
import time
from typing import List, Optional

import httpx

from . import (HEADERS, RateLimiter, TIMEOUT, fetch_text, load_registry, log,
               registry_for_article, safe, store, warn)
from .registry import GDELT_REGISTRY_ID

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# GDELT asks for one request every 5 seconds; NVD-style politeness applies here too.
_gdelt_limit = RateLimiter(5.5)

STOPWORDS = {
    "how", "what", "why", "when", "which", "where", "who", "should", "could",
    "would", "will", "can", "may", "might", "does", "do", "did", "is", "are",
    "was", "were", "be", "been", "the", "a", "an", "and", "or", "but", "if",
    "of", "to", "in", "on", "for", "with", "as", "at", "by", "from", "over",
    "next", "years", "year", "its", "it", "that", "this", "these", "those",
    "their", "there", "them", "they", "we", "our", "us", "most", "more", "less",
    "than", "into", "out", "up", "down", "about", "across", "become", "becomes",
    "becoming", "remain", "remains", "evolve", "change", "changes", "changing",
    "future", "today", "new", "rely", "relies", "happens", "happen", "look",
    "like", "make", "made", "take", "takes", "use", "used", "using", "need",
    "needs", "available", "time", "way", "ways", "part", "much", "many",
}

# One-term -> OR-group expansions. Keeps a narrow question from returning nothing.
ALIASES = {
    "drone": '("drone" OR "drones" OR "UAS" OR "UAV")',
    "drones": '("drone" OR "drones" OR "UAS" OR "UAV")',
    "uas": '("counter-UAS" OR "UAS" OR "drone")',
    "counter-uas": '("counter-UAS" OR "counter-drone" OR "C-UAS")',
    "jamming": '("jamming" OR "jammer" OR "electronic warfare")',
    "gnss": '("GNSS" OR "GPS" OR "satellite navigation")',
    "procurement": '("procurement" OR "acquisition")',
    "autonomy": '("autonomy" OR "autonomous")',
}


def derive_query(text: str, max_terms: int = 4) -> str:
    """Turn a strategic question into a GDELT query.

    GDELT rejects unquoted hyphens ('counter-UAS' is an illegal character
    sequence unless quoted) and ANDs bare space-separated terms — so a long
    question ANDed verbatim returns nothing. We keep the few most distinctive
    terms and expand known ones into OR-groups.
    """
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]+", text.lower())
    terms: List[str] = []
    for token in tokens:
        if token in STOPWORDS or len(token) < 3 or token in terms:
            continue
        terms.append(token)
        if len(terms) >= max_terms:
            break

    parts = []
    for term in terms:
        if term in ALIASES:
            parts.append(ALIASES[term])
        elif "-" in term:
            parts.append('"%s"' % term)      # hyphens MUST be quoted
        else:
            parts.append(term)
    return " ".join(parts)


def gdelt_search(query: str, timespan: str = "3months", maxrecords: int = 20,
                 sourcecountry: Optional[str] = None, attempts: int = 3) -> List[dict]:
    """Query GDELT DOC 2.0.

    GDELT signals failure with HTTP 200 and a plain-text body ("One or more of
    your keywords contained an illegal character...", rate-limit notices), so a
    bare .json() would raise an opaque decode error. We detect non-JSON bodies
    and surface GDELT's own message.
    """
    params = {"query": query, "mode": "artlist", "format": "json",
              "timespan": timespan, "maxrecords": str(maxrecords)}
    if sourcecountry:
        params["sourcecountry"] = sourcecountry

    delay_notice = None
    for attempt in range(1, attempts + 1):
        _gdelt_limit.wait()
        resp = httpx.get(GDELT_URL, params=params, headers=HEADERS,
                         timeout=TIMEOUT, follow_redirects=True)
        body = (resp.text or "").strip()

        if resp.status_code == 429 or body.startswith("Please limit requests"):
            # GDELT's documented spacing is 5s, but once tripped it holds an IP
            # in a cooldown far longer than that. Escalate hard rather than
            # tapping the endpoint repeatedly.
            delay_notice = "rate limited"
            backoff = 20 * (2 ** (attempt - 1))
            warn("GDELT rate limit (attempt %d/%d) — sleeping %ds"
                 % (attempt, attempts, backoff))
            time.sleep(backoff)
            _gdelt_limit.min_interval = max(_gdelt_limit.min_interval, 8)
            continue
        resp.raise_for_status()

        if not body.startswith("{"):
            raise ValueError("GDELT rejected the query: " + body[:160])

        articles = resp.json().get("articles", []) or []
        log("  GDELT returned %d articles for: %s" % (len(articles), query))
        return articles

    raise RuntimeError("GDELT unavailable after %d attempts (%s)" % (attempts, delay_notice))


def collect_gdelt(sb, query, limit=10, timespan="3months",
                  sourcecountry=None, dry_run=False) -> int:
    registry_rows = load_registry(sb, dry_run)
    # over-fetch: some articles will be unreachable or too thin to store
    articles = gdelt_search(query, timespan=timespan, maxrecords=limit * 2,
                            sourcecountry=sourcecountry)

    stored = mapped = fallback = 0
    for article in articles:
        if stored >= limit:
            break
        url = article.get("url")
        if not url:
            continue

        registry_id = registry_for_article(url, registry_rows)
        if registry_id == GDELT_REGISTRY_ID:
            fallback += 1
            note = "fallback aggregator, domain=%s" % (article.get("domain") or "?")
        else:
            mapped += 1
            note = "mapped %s -> publisher tier" % (article.get("domain") or "?")

        got = safe(url, fetch_text, url)
        if not got:
            continue
        title, text = got
        log("    %s" % note)
        if store(sb, registry_id, url, article.get("title") or title, text,
                 published_on=_gdelt_date(article.get("seendate")), dry_run=dry_run):
            stored += 1

    log("  domain mapping: %d matched a registry publisher, %d fell back to %s"
        % (mapped, fallback, GDELT_REGISTRY_ID))
    return stored


def _gdelt_date(seendate) -> Optional[str]:
    """GDELT seendate looks like 20260915T120000Z."""
    if not seendate or len(str(seendate)) < 8:
        return None
    raw = str(seendate)
    return "%s-%s-%s" % (raw[0:4], raw[4:6], raw[6:8])


def collect_serper(sb, query, pillar=None, limit=5, dry_run=False) -> int:
    """Site-scoped search over the Tier 1/2 registry rows whose method='search'."""
    key = os.environ.get("SERPER_API_KEY")
    rows = [r for r in load_registry(sb, dry_run) if r["method"] == "search"
            and (pillar is None or pillar in (r.get("pillars") or []))]
    if not rows:
        return 0
    if not key:
        warn("no SERPER_API_KEY — skipping %d site-scoped search rows "
             "(GDELT lane still ran)" % len(rows))
        return 0

    stored = 0
    for row in rows:
        host = row["url"].split("//")[-1].split("/")[0]
        try:
            resp = httpx.post("https://google.serper.dev/search", timeout=TIMEOUT,
                              headers={"X-API-KEY": key},
                              json={"q": "site:%s %s" % (host, query), "num": limit})
            resp.raise_for_status()
            organic = resp.json().get("organic", [])[:limit]
        except Exception as exc:
            warn("serper %s: %s" % (row["publisher"], exc))
            continue

        log("[Tier %d] %s — %d hits" % (row["tier"], row["publisher"], len(organic)))
        for item in organic:
            link = item.get("link")
            if not link:
                continue
            got = safe(link, fetch_text, link)
            if not got:
                continue
            title, text = got
            if store(sb, row["id"], link, item.get("title") or title, text, dry_run=dry_run):
                stored += 1
    return stored


def run(sb, question_id=None, query=None, pillar=None, limit=10,
        timespan="3months", sourcecountry=None, dry_run=False) -> int:
    if question_id:
        question = None
        if sb is not None and not dry_run:
            rows = sb.table("questions").select("id,text,pillar").eq(
                "id", question_id).execute().data
            question = rows[0] if rows else None
        if not question:
            raise SystemExit("question %s not found — seed the question bank first"
                             % question_id)
        pillar = pillar or question["pillar"]
        query = derive_query(question["text"])
        log("LANE B · question %s (%s)" % (question_id, pillar))
        log('  "%s"' % question["text"])
        log("  derived GDELT query: %s" % query)
    elif query:
        query = derive_query(query)
        log("LANE B · ad-hoc query")
        log("  derived GDELT query: %s" % query)
    else:
        raise SystemExit("lane b needs --question-id or --query")

    total = safe("gdelt", collect_gdelt, sb, query, limit, timespan,
                 sourcecountry, dry_run) or 0
    total += safe("serper", collect_serper, sb, query, pillar, min(limit, 5),
                  dry_run) or 0
    log("LANE B complete — %d documents" % total)
    return total
