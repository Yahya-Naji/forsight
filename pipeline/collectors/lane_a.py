"""LANE A — scheduled feeds (registry method 'rss' or 'scrape').

Runs unattended on a daily cron. Breadth over precision: everything Lane A
stores still has to survive the Jev relevance gate and the extractor, so the
job here is coverage, not judgement.

  python collect.py --lane a --pillar CYBERSECURITY --limit 3
"""
from __future__ import annotations

import feedparser

import httpx

from . import (HEADERS, MIN_TEXT, TIMEOUT, child_links, fetch_text,
               load_registry, log, registry_for_article, safe, store, warn)

# An RSS summary is publisher-syndicated text, so it is a legitimate (if thin)
# document when the article page itself is unreachable. Floor is lower than
# MIN_TEXT because summaries run 150-400 chars.
RSS_SUMMARY_FLOOR = 150

# Interstitials that return HTTP 200 with a body: CDN denials, bot walls and
# JS-only shells. Their text can clear the length floor, so they are detected by
# content, not by status code.
BLOCK_MARKERS = (
    "access denied", "you don't have permission", "403 forbidden",
    "are you a robot", "enable javascript", "checking your browser",
    "request unsuccessful", "captcha",
)

# Soft-404s: the server answers 200 and serves an error page. Detected by
# content, since the status code says nothing is wrong.
NOTFOUND_MARKERS = (
    "404", "page not found", "page cannot be found", "page doesn't exist",
    "page does not exist", "no longer available",
)


def _looks_blocked(text: str, title: str = "") -> bool:
    head = (text or "")[:600].lower()
    if any(marker in head for marker in BLOCK_MARKERS):
        return True
    probe = ((title or "") + " " + head[:180]).lower()
    return any(marker in probe for marker in NOTFOUND_MARKERS)


def _published(entry):
    """Feed date -> ISO date string, or None if the feed omits/garbles it."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    try:
        return "%04d-%02d-%02d" % (parsed[0], parsed[1], parsed[2])
    except Exception:
        return None


def _summary(entry) -> str:
    """Plain-text summary from a feed entry, tags stripped."""
    raw = entry.get("summary") or entry.get("description") or ""
    if not raw:
        return ""
    if "<" in raw:
        from bs4 import BeautifulSoup
        raw = BeautifulSoup(raw, "html.parser").get_text(" ")
    return " ".join(raw.split())


def collect_rss(sb, row, limit, dry_run=False):
    feed = feedparser.parse(row["url"])
    entries = getattr(feed, "entries", [])[:limit]
    if not entries:
        warn("no entries from %s" % row["publisher"])
        return 0
    stored = 0
    for entry in entries:
        link = entry.get("link")
        if not link:
            continue
        got = safe(link, fetch_text, link)
        title, text, floor = (got[0], got[1], None) if got else (None, "", None)

        # The article page can fail in three ways that all look different:
        # unreachable, a CDN denial served as HTTP 200, or a JS-only stub. In
        # each case the feed's own summary is publisher-syndicated text and is
        # better than losing a Tier-1 item.
        if not got or _looks_blocked(text, title or "") or len(text) < MIN_TEXT:
            summary = _summary(entry)
            if summary:
                reason = ("blocked" if got and _looks_blocked(text, title or "")
                          else "unreachable" if not got else "stub page")
                title = entry.get("title") or link
                text = "%s. %s" % (entry.get("title", ""), summary)
                floor = RSS_SUMMARY_FLOOR
                log("    (%s — using feed summary, %d chars)" % (reason, len(text)))
            elif not got:
                continue

        if store(sb, row["id"], link, entry.get("title") or title, text,
                 published_on=_published(entry), dry_run=dry_run, min_chars=floor):
            stored += 1
    return stored


def collect_scrape(sb, row, limit, dry_run=False):
    got = safe(row["url"], fetch_text, row["url"])
    if not got:
        return 0
    title, text = got
    if _looks_blocked(text, title):
        warn("error/blocked page, skipped: %s" % row["publisher"])
        return 0
    return 1 if store(sb, row["id"], row["url"], title, text, dry_run=dry_run) else 0


def run(sb, pillar, limit=5, dry_run=False):
    rows = [r for r in load_registry(sb, dry_run)
            if r["method"] in ("rss", "scrape") and pillar in (r.get("pillars") or [])]
    if not rows:
        warn("no Lane A sources registered for pillar %s" % pillar)
        return 0

    log("LANE A · %s · %d scheduled sources" % (pillar, len(rows)))
    total = 0
    for row in sorted(rows, key=lambda r: r["tier"]):
        log("[Tier %d] %s (%s)" % (row["tier"], row["publisher"], row["method"]))
        if row["method"] == "rss":
            total += collect_rss(sb, row, limit, dry_run) or 0
        else:
            total += collect_scrape(sb, row, limit, dry_run) or 0
    log("LANE A complete — %d documents" % total)
    return total


POLICY_KEYWORDS = ("cyber", "security", "strategy", "policy", "framework",
                   "advisory", "alert", "guideline", "regulation", "defence",
                   "defense", "digital", "ai", "report")


def run_urls(sb, urls, dry_run=False, depth=0):
    """Ingest specific documents by URL.

    Scheduled sweeps give breadth; this gives precision. The registry row is
    resolved from the URL's own domain, so tier — and therefore evidence class —
    is identical to what the source would receive through any other lane.
    """
    rows = load_registry(sb, dry_run)

    if depth:
        expanded = list(urls)
        for seed in urls:
            try:
                resp = httpx.get(seed, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
                kids = child_links(seed, resp.text, POLICY_KEYWORDS)
                log("  %d child link(s) from %s" % (len(kids), seed[:58]))
                expanded += kids
            except Exception as exc:
                warn("link discovery failed for %s: %s" % (seed[:50], exc))
                _gap(sb, seed, "link discovery failed: %s" % exc, dry_run)
        urls = list(dict.fromkeys(expanded))

    stored = 0
    for url in urls:
        registry_id = registry_for_article(url, rows)
        got = safe(url, fetch_text, url)
        if not got:
            # Silence would read as "nothing to find here". Record why.
            _gap(sb, url, "unreachable during targeted ingest", dry_run)
            continue
        title, text = got
        if _looks_blocked(text, title):
            warn("error/blocked page, skipped: %s" % url[:70])
            _gap(sb, url, "served a block or error page", dry_run)
            continue
        if store(sb, registry_id, url, title, text, dry_run=dry_run):
            stored += 1
    log("targeted ingest complete — %d documents" % stored)
    return stored


def _gap(sb, url, reason, dry_run=False):
    """An unreachable Tier-1 source is a research gap, not a silent zero."""
    if dry_run or sb is None:
        return
    try:
        sb.table("research_gaps").insert({
            "gap": ("Source not collected: %s — %s" % (url, reason))[:500],
            "raised_by": "collect.lane_a"}).execute()
    except Exception:
        pass
