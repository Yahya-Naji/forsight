"""Shared collector plumbing for the three lanes.

Politeness (robots.txt, UA, timeout), storage (upsert on url), and the
domain -> registry_id mapping that keeps the publisher's TIER attached to every
document. Tier is what rules.py turns into evidence class, so a document stored
against the wrong registry row silently corrupts the symbolic layer downstream.
"""
from __future__ import annotations

import time
import os
from typing import Dict, List, Optional
from urllib import robotparser
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .registry import DOMAIN_ALIASES, GDELT_REGISTRY_ID, as_dicts

UA = "foresight-poc/0.2 (strategic-foresight research collector)"
HEADERS = {"User-Agent": UA, "Accept-Language": "en"}
TIMEOUT = 30
MAX_TEXT = 60000
MIN_TEXT = 300          # below this a "document" is a nav stub or a paywall page

_robots: Dict[str, Optional[robotparser.RobotFileParser]] = {}


def log(msg: str) -> None:
    print(msg, flush=True)


def warn(msg: str) -> None:
    print("  ! " + msg, flush=True)


# --------------------------------------------------------------------------
# politeness
# --------------------------------------------------------------------------
def robots_allowed(url: str) -> bool:
    """Honour robots.txt.

    Fails OPEN when robots.txt is missing or unreadable (absence is not a
    prohibition) and CLOSED only on an explicit Disallow.
    """
    try:
        parts = urlparse(url)
        root = parts.scheme + "://" + parts.netloc
    except Exception:
        return True
    if not parts.netloc:
        return True

    if root not in _robots:
        parser = None
        try:
            resp = httpx.get(root + "/robots.txt", headers=HEADERS,
                             timeout=10, follow_redirects=True)
            if resp.status_code < 400 and resp.text.strip():
                parser = robotparser.RobotFileParser()
                parser.parse(resp.text.splitlines())
        except Exception:
            parser = None
        _robots[root] = parser

    parser = _robots[root]
    if parser is None:
        return True
    try:
        return parser.can_fetch(UA, url)
    except Exception:
        return True


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# stealth fallback — camofox-browser
# --------------------------------------------------------------------------
# Some publishers we are entitled to read refuse a plain client outright. NATO
# ACT and NCIA return 403 to this collector, which cost the electronic-warfare
# pillar its most relevant Tier-1 material — the layered counter-UAS
# experimentation campaign — and left that pillar too thin to produce findings.
#
# camofox-browser (MIT, github.com/jo-inc/camofox-browser) wraps Camoufox, a
# Firefox fork with fingerprint spoofing below the JS layer, behind a local REST
# API. Run it and set CAMOFOX_URL; leave it unset and nothing changes.
#
# WHAT THIS DOES NOT DO: it does not touch robots.txt, which is still honoured
# before any fetch is attempted, and it does not change a document's publisher
# or tier. How a page was retrieved is a transport detail; what it is worth is
# decided by the registry, exactly as before.

CAMOFOX_TIMEOUT = 90


def camofox_url() -> Optional[str]:
    return (os.environ.get("CAMOFOX_URL") or "").strip().rstrip("/") or None


def fetch_via_camofox(url: str):
    """(title, text) through the stealth browser, or None if it cannot serve it.

    Never raises: this is a fallback, and a fallback that breaks collection is
    worse than the 403 it was meant to solve.
    """
    base = camofox_url()
    if not base:
        return None
    tab = None
    try:
        r = httpx.post("%s/tabs" % base, json={"userId": "foresight", "url": url},
                       timeout=CAMOFOX_TIMEOUT)
        r.raise_for_status()
        tab = (r.json() or {}).get("id") or (r.json() or {}).get("tabId")
        if not tab:
            return None
        snap = httpx.get("%s/tabs/%s/snapshot" % (base, tab),
                         params={"userId": "foresight"}, timeout=CAMOFOX_TIMEOUT)
        snap.raise_for_status()
        body = snap.json() if snap.headers.get("content-type", "").startswith("application/json") \
            else {"text": snap.text}
        # The API has moved field names between versions; take the first that
        # carries prose rather than pinning to one and failing silently.
        text = ""
        for key in ("markdown", "text", "content", "snapshot", "html"):
            val = body.get(key) if isinstance(body, dict) else None
            if isinstance(val, str) and len(val) > len(text):
                text = val
        if "<" in text and ">" in text:
            text = BeautifulSoup(text, "html.parser").get_text(" ")
        text = " ".join(text.split())[:MAX_TEXT]
        title = (body.get("title") if isinstance(body, dict) else None) or url
        return (str(title).strip() or url, text) if text else None
    except Exception as exc:
        warn("camofox could not fetch %s — %s" % (url[:60], str(exc)[:70]))
        return None
    finally:
        if tab:
            try:
                httpx.delete("%s/tabs/%s" % (base, tab),
                             params={"userId": "foresight"}, timeout=20)
            except Exception:
                pass


def fetch_text(url: str, respect_robots: bool = True):
    """Return (title, cleaned_text). Raises on any reason the page is unusable."""
    if respect_robots and not robots_allowed(url):
        raise PermissionError("robots.txt disallows " + url)

    try:
        resp = httpx.get(url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # 403/429 from a publisher we are allowed to read is a bot check, not a
        # refusal of access. Anything else is a real error and stays one.
        if exc.response.status_code not in (401, 403, 429) or not camofox_url():
            raise
        log("  → %s returned %d; retrying through camofox"
            % (host_of(url), exc.response.status_code))
        got = fetch_via_camofox(url)
        if not got:
            raise
        return got

    ctype = resp.headers.get("content-type", "").lower()
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        return _pdf_text(url, resp.content)
    if ctype and not any(k in ctype for k in ("html", "xml", "text")):
        raise ValueError("non-text content-type: " + ctype)

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "form", "aside", "noscript"]):
        tag.decompose()

    title = url
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    text = " ".join(soup.get_text(" ").split())[:MAX_TEXT]
    return title, text


def _pdf_text(url: str, blob: bytes):
    """Government policy lives in PDFs; refusing them loses the Tier-1 layer."""
    import io
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(blob))
    pages = []
    for page in reader.pages[:60]:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    title = (reader.metadata or {}).get("/Title") or url.rsplit("/", 1)[-1]
    text = " ".join(" ".join(pages).split())[:MAX_TEXT]
    return str(title).strip() or url, text


def child_links(url: str, html: str, keywords, limit: int = 8):
    """Same-site links from a seed page that look like policy or advisory pages.

    Index pages are navigation, not evidence. One level down is where the
    strategy documents and advisories actually live.
    """
    from urllib.parse import urljoin
    soup = BeautifulSoup(html, "html.parser")
    root, out, seen = host_of(url), [], set()
    for a in soup.find_all("a", href=True):
        link = urljoin(url, a["href"].split("#")[0])
        if not link.startswith("http") or link in seen:
            continue
        if host_of(link) != root:
            continue
        blob = (link + " " + a.get_text(" ")).lower()
        if link.lower().endswith(".pdf") or any(k in blob for k in keywords):
            seen.add(link)
            out.append(link)
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------
# storage
# --------------------------------------------------------------------------
def store(sb, registry_id: str, url: str, title: str, text: str,
          published_on: Optional[str] = None, dry_run: bool = False,
          min_chars: Optional[int] = None) -> bool:
    """Upsert one document. `on_conflict=url` makes re-collection idempotent."""
    floor = MIN_TEXT if min_chars is None else min_chars
    if not text or len(text) < floor:
        warn("too short (%d chars), skipped: %s" % (len(text or ""), url[:70]))
        return False

    row = {"registry_id": registry_id, "url": url,
           "title": (title or url)[:500], "raw_text": text}
    if published_on:
        row["published_on"] = published_on

    if dry_run:
        log("  [dry-run] %-13s %s" % (registry_id, (title or url)[:62]))
        return True

    sb.table("documents").upsert(row, on_conflict="url").execute()
    log("  stored [%s] %s" % (registry_id, (title or url)[:62]))
    return True


# --------------------------------------------------------------------------
# domain -> registry mapping (the tier-integrity rule)
# --------------------------------------------------------------------------
def host_of(url: str) -> str:
    try:
        host = (urlparse(url).netloc or "").lower().split(":")[0]
    except Exception:
        return ""
    return host[4:] if host.startswith("www.") else host


def load_registry(sb, dry_run: bool = False) -> List[dict]:
    """Live registry when we have a DB, the static copy when we don't."""
    if dry_run or sb is None:
        return as_dicts()
    try:
        rows = sb.table("source_registry").select(
            "id,tier,publisher,url,method,pillars,notes,archived_at").execute().data
        return rows or as_dicts()
    except Exception as exc:
        warn("registry read failed (%s) — using static copy" % exc)
        return as_dicts()


def map_domain(url: str, registry_rows: List[dict]) -> Optional[str]:
    """Map an article URL to the registry row for its ACTUAL publisher.

    Most-specific match wins, so `services.nvd.nist.gov` binds to the NVD row
    rather than to a broader `nist.gov` row. Returns None when nothing matches;
    the caller then falls back to the aggregator id.
    """
    host = host_of(url)
    if not host:
        return None
    candidates = [(host_of(r.get("url", "")), r["id"]) for r in registry_rows]
    candidates += list(DOMAIN_ALIASES.items())

    best_id, best_len = None, -1
    for cand, registry_id in candidates:
        if not cand or cand == "api.gdeltproject.org":
            continue
        if host == cand or host.endswith("." + cand):
            if len(cand) > best_len:
                best_id, best_len = registry_id, len(cand)
    return best_id


def registry_for_article(url: str, registry_rows: List[dict]) -> str:
    """Tier integrity: an article keeps its publisher's tier, not the
    aggregator's. Only genuinely unknown domains land on SRC-API-001."""
    return map_domain(url, registry_rows) or GDELT_REGISTRY_ID


# --------------------------------------------------------------------------
# resilience
# --------------------------------------------------------------------------
def safe(label: str, fn, *args, **kwargs):
    """Run a collection step; log and continue. One bad source never kills a run."""
    try:
        return fn(*args, **kwargs)
    except PermissionError as exc:
        warn("robots: %s" % exc)
    except httpx.HTTPStatusError as exc:
        warn("%s -> HTTP %s" % (label, exc.response.status_code))
    except Exception as exc:
        warn("%s -> %s: %s" % (label, type(exc).__name__, exc))
    return None


class RateLimiter:
    """Minimum spacing between calls to one API (GDELT asks for 5s; NVD 6s)."""

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._last = 0.0

    def wait(self) -> None:
        gap = time.time() - self._last
        if gap < self.min_interval:
            time.sleep(self.min_interval - gap)
        self._last = time.time()
