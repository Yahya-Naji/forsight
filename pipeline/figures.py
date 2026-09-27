"""Find the figures in collected documents and decide which may be cited.

Reports have been text-only, which understates what the sources actually
contain: threat reports and national strategies publish the charts their
conclusions rest on, and a brief that describes a trend in prose while the
source shows it in a plot is doing less than its evidence allows.

Two rules keep figures honest.

First, a figure is not automatically evidence. An article about supply-chain
intrusions carries both a plot of intrusion-set growth and a stock photograph
of a server room. The plot is evidence; the photograph lends the publisher's
authority to a page while carrying none of its information. So the model
proposes a kind and a description, and `rules.figure_is_informative` decides
admission — the model never sets that column.

Second, provenance runs through the document. A figure inherits publisher, tier
and date from the page it was found on, so a cited figure is traceable exactly
the way a cited claim is, and the reference list can name both together.

This runs as its own pass rather than inside the collectors, so figures can be
backfilled across documents already collected.

  python figures.py --pillar CYBERSECURITY
  python figures.py --pillar CYBERSECURITY --limit 20 --recheck
"""
from __future__ import annotations

import argparse
import re
import time
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

import config
import llm
import rules
from config import db
from collectors import HEADERS, TIMEOUT, robots_allowed

# Filename and path fragments that mark furniture rather than content. Cheap,
# deterministic, and run before any model call — most images on a news page are
# navigation, and paying a model to tell us that is waste.
JUNK = re.compile(
    r"(logo|icon|favicon|avatar|sprite|badge|banner|button|arrow|chevron|"
    r"spinner|placeholder|pixel|tracking|1x1|spacer|divider|bullet|"
    r"social|share|twitter|facebook|linkedin|youtube|rss|subscribe|"
    r"newsletter|cookie|consent|/ads?/|advert|sponsor|thumbnail_small)", re.I)

# Below this, an image cannot be a readable chart at print size.
MIN_EDGE = 220


def _int(value) -> Optional[int]:
    try:
        return int(str(value).strip().rstrip("px"))
    except (TypeError, ValueError):
        return None


def _largest_in_srcset(srcset: str, base: str) -> Optional[str]:
    """Responsive images list several sizes; the largest is the one worth citing."""
    best, best_w = None, -1
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        width = _int(bits[1].rstrip("w")) if len(bits) > 1 else 0
        if (width or 0) > best_w:
            best, best_w = urljoin(base, bits[0]), width or 0
    return best


class Candidate(BaseModel):
    url: str
    alt: str = ""
    caption: str = ""
    credit: str = ""
    width: Optional[int] = None
    height: Optional[int] = None


def candidates(page_url: str, html: str) -> List[Candidate]:
    """Images on the page that could plausibly carry information.

    Deliberately permissive about what it keeps and strict about what it drops:
    a missed chart is a smaller loss than a stock photo presented as evidence,
    and the kind classifier downstream is the thing that separates them.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["nav", "footer", "header", "aside", "script", "style"]):
        tag.decompose()

    found, seen = [], set()

    def add(src, alt="", caption="", credit="", width=None, height=None):
        if not src or src.startswith("data:"):
            return
        url = urljoin(page_url, src.split("#")[0])
        if not url.startswith("http") or url in seen:
            return
        if JUNK.search(url):
            return
        if (width and width < MIN_EDGE) or (height and height < MIN_EDGE):
            return
        seen.add(url)
        found.append(Candidate(url=url, alt=(alt or "").strip()[:400],
                               caption=(caption or "").strip()[:600],
                               credit=(credit or "").strip()[:200],
                               width=width, height=height))

    # A <figcaption> is the strongest available signal that the publisher
    # considered the image part of the argument rather than the styling.
    for fig in soup.find_all("figure"):
        cap = fig.find("figcaption")
        caption = cap.get_text(" ", strip=True) if cap else ""
        img = fig.find("img")
        if not img:
            continue
        src = img.get("src") or _largest_in_srcset(img.get("srcset", ""), page_url)
        add(src, img.get("alt", ""), caption,
            width=_int(img.get("width")), height=_int(img.get("height")))

    for img in soup.find_all("img"):
        src = img.get("src") or _largest_in_srcset(img.get("srcset", ""), page_url)
        add(src, img.get("alt", ""), "",
            width=_int(img.get("width")), height=_int(img.get("height")))

    # The social-card image. Usually the hero photograph, so it is collected and
    # then almost always classified PHOTO and refused — which is the rule
    # working, not the extractor failing.
    for prop in ("og:image", "twitter:image"):
        tag = soup.find("meta", attrs={"property": prop}) or \
              soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            add(tag["content"], alt="social card image")

    return found


# --------------------------------------------------------------------------
# classification — the model proposes, rules.py decides
# --------------------------------------------------------------------------
CLASSIFY_PROMPT = """You are cataloguing images found in a published document, to
decide which carry information a policy reader could verify.

For each numbered image you are given the file URL, its alt text and its caption
if the page had one. You cannot see the image. Judge ONLY from that text, and
say UNKNOWN when the text does not tell you — guessing CHART because the article
is about data is the error to avoid.

kind, one of:
  CHART        plotted data — bar, line, pie, scatter, histogram
  DIAGRAM      architecture, flow, taxonomy, model, framework
  MAP          geographic
  TABLE_IMAGE  a table rendered as an image
  SCREENSHOT   a capture of an interface, tool, document or artefact
  TIMELINE     events along time
  PHOTO        a photograph of people, places, equipment or events
  LOGO         a mark, wordmark or emblem
  UNKNOWN      the text does not say

describes: one sentence on what the image shows, for a reader who cannot see it.
Write it from the caption and alt text only. If they say nothing, return "".

DOCUMENT: {title}
{items}
"""


class FigureVerdict(BaseModel):
    index: int
    kind: str
    describes: str


class FigureBatch(BaseModel):
    verdicts: list[FigureVerdict]


def classify(title: str, cands: List[Candidate], batch_size: int = 25):
    """Returns a list of (kind, describes) aligned with `cands`."""
    out = [("UNKNOWN", "")] * len(cands)
    for start in range(0, len(cands), batch_size):
        chunk = cands[start:start + batch_size]
        rendered = "\n\n".join(
            "[%d]\nFILE: %s\nALT: %s\nCAPTION: %s"
            % (start + i, c.url.rsplit("/", 1)[-1][:120], c.alt or "—", c.caption or "—")
            for i, c in enumerate(chunk))
        result = llm.structured(
            CLASSIFY_PROMPT.format(title=title[:200], items=rendered),
            FigureBatch, fast=True, effort="low")
        for v in result.verdicts:
            if 0 <= v.index < len(out):
                out[v.index] = ((v.kind or "UNKNOWN").upper().strip(),
                                (v.describes or "").strip()[:500])
    return out


# --------------------------------------------------------------------------
# reachability
# --------------------------------------------------------------------------
IMG_HEADERS = {**HEADERS, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}


def check_reachable(url: str, attempts: int = 2):
    """(reachable, content_type, bytes). A broken image reads as a broken
    report, so this is checked before a figure is offered to a brief.

    Retried, because the first run condemned the single most useful figure it
    found — a chart of targeted industries — on one throttled response from a
    CDN that served it happily a minute later. Marking a good figure
    unreachable silently removes evidence, so a single failure is not enough.
    """
    for attempt in range(attempts):
        try:
            resp = httpx.head(url, headers=IMG_HEADERS, timeout=20, follow_redirects=True)
            if resp.status_code >= 400 or "image" not in resp.headers.get("content-type", ""):
                # Some CDNs refuse HEAD; a ranged GET settles it without the payload.
                resp = httpx.get(url, headers={**IMG_HEADERS, "Range": "bytes=0-2047"},
                                 timeout=20, follow_redirects=True)
            ctype = resp.headers.get("content-type", "").split(";")[0].strip()
            size = _int(resp.headers.get("content-length"))
            if resp.status_code < 400 and ctype.startswith("image/"):
                return True, ctype or None, size
        except Exception:
            pass
        if attempt + 1 < attempts:
            time.sleep(1.5)
    return False, None, None


def next_id(sb) -> int:
    rows = sb.table("figures").select("id").execute().data
    nums = [int(m.group(1)) for r in rows
            if (m := re.match(r"FIG-(\d+)$", r["id"]))]
    return max(nums, default=0) + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    ap.add_argument("--pillar", required=True)
    ap.add_argument("--limit", type=int, default=60, help="documents to walk")
    ap.add_argument("--recheck", action="store_true",
                    help="re-test reachability of figures already stored")
    a = ap.parse_args()
    config.update_run(getattr(a, "run_id", None), stage="figures", status="RUNNING")
    sb = db()

    if a.recheck:
        rows = sb.table("figures").select("id,url").eq("pillar", a.pillar).execute().data
        gone = 0
        for r in rows:
            ok, ctype, size = check_reachable(r["url"])
            gone += (not ok)
            sb.table("figures").update(
                {"reachable": ok, "content_type": ctype, "bytes": size,
                 "checked_at": "now()"}).eq("id", r["id"]).execute()
        print("rechecked %d figures, %d unreachable" % (len(rows), gone))
        return

    # Documents that produced evidence for this pillar are the ones whose
    # figures a report on this pillar could legitimately cite.
    ev = sb.table("evidence").select("id").eq("pillar", a.pillar).execute().data
    ev_ids = [r["id"] for r in ev]
    doc_ids = set()
    for i in range(0, len(ev_ids), 50):
        for r in (sb.table("evidence_sources").select("document_id")
                  .in_("evidence_id", ev_ids[i:i + 50]).execute().data):
            doc_ids.add(r["document_id"])
    docs = [d for d in sb.table("documents").select("id,url,title")
            .in_("id", list(doc_ids)).execute().data][:a.limit]
    print("%d documents behind %s evidence\n" % (len(docs), a.pillar))

    seq = next_id(sb)
    kept = skipped = 0
    for doc in docs:
        url = doc["url"]
        if url.lower().endswith(".pdf"):
            continue                       # figures inside PDFs need rasterising
        if not robots_allowed(url):
            print("  robots: %s" % url[:78]); continue
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
            resp.raise_for_status()
            if "html" not in resp.headers.get("content-type", "").lower():
                continue
            cands = candidates(url, resp.text)
        except Exception as exc:
            print("  ! %s — %s" % (urlparse(url).netloc, str(exc)[:60]))
            continue
        if not cands:
            continue

        known = {r["url"] for r in sb.table("figures").select("url")
                 .eq("document_id", doc["id"]).execute().data}
        cands = [c for c in cands if c.url not in known]
        if not cands:
            continue

        verdicts = classify(doc.get("title") or url, cands)
        print("  %-38s %d candidate(s)" % (urlparse(url).netloc[:38], len(cands)))
        for cand, (kind, describes) in zip(cands, verdicts):
            admit, reason = rules.figure_is_informative(kind, cand.caption, cand.alt)

            # A near miss — the kind was plausible but the page gave no caption —
            # is recorded, because "three images looked like charts and none
            # carried a caption" says something auditable about the source.
            # Obvious furniture is dropped without a row.
            near_miss = not admit and kind in rules.INFORMATIVE_KINDS
            if not admit and not near_miss:
                skipped += 1
                print("      – %-11s %s" % (kind, reason[:58]))
                continue

            ok, ctype, size = (check_reachable(cand.url) if admit else (None, None, None))
            fid = "FIG-%03d" % seq
            sb.table("figures").insert({
                "id": fid, "document_id": doc["id"], "pillar": a.pillar,
                "url": cand.url, "caption": cand.caption or None,
                "alt": cand.alt or None, "kind": kind,
                "informative": admit,                # rules.py decided this
                "refused_reason": None if admit else reason,
                "describes": describes or cand.caption or cand.alt or None,
                "width": cand.width, "height": cand.height,
                "credit": cand.credit or None,
                "reachable": ok, "content_type": ctype, "bytes": size,
                "checked_at": "now()" if admit else None}).execute()
            seq += 1
            if admit:
                kept += 1
                print("      ✓ %-11s %s  %s%s" % (kind, fid,
                      (describes or cand.caption or "")[:54],
                      "" if ok else "  [UNREACHABLE]"))
            else:
                skipped += 1
                print("      – %-11s %s — %s" % (kind, fid, reason[:48]))

    print("\n%d figure(s) admitted, %d refused as decoration" % (kept, skipped))
    config.update_run(getattr(a, "run_id", None), counts={"figures": kept})


if __name__ == "__main__":
    main()
