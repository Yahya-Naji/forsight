# Neurosymbolic Foresight Agent

Strategic-foresight system for the Tawazun Council across four pillars —
Cybersecurity, AI, Electronic Warfare, Procurement.

Not prompt-based generation. Every fact is a typed, sourced row in Postgres;
rules assign class, confidence and signal strength; the model only extracts and
drafts, and never sets a score. A report whose citations do not resolve is
withheld rather than published.

```
                    ┌─ LANE A  scheduled feeds (rss + scrape), daily cron
source_registry ────┼─ LANE B  question-driven search (GDELT + site search)
  27 tiered rows    └─ LANE C  structured APIs (ATT&CK, NVD) ──┐
                                                               │
          Lanes A+B → documents → extract.py (LLM + Pydantic) ─┤
                                                               ▼
                    evidence → decisions.py (Gate 3) → rules.py → synthesize.py
                                                               │
                      generate.py (bounded, retry-on-failure)  ▼
                                    verify.py → reports + generation_ledger
                                                               │
                                       Next.js console ◄───────┘
```

## What makes it defensible

| Guarantee | Enforced by |
|---|---|
| Corroboration counts **independent publishers**, never evidence rows | `rules.py` |
| Class, confidence, strength, L×I are **computed**, never authored | `rules.py`, `synthesize.py` |
| `env_layer=UAE` only when a quote names the UAE — not "Middle East, Gulf or UAE" | `layers.py` |
| A UAE gap claim needs ≥2 UAE rows from ≥2 publishers, or the gate stays OPEN | `rules.py` |
| Sections failing verification are retried, then **withheld** | `generate.py` + `verify.py` |
| References are assembled mechanically, deduped by document | `generate.py` |
| Rejected proposals become research gaps, not silence | `synthesize.py`, `collect.py` |

## Quick start

```bash
make setup                  # venv + python deps + npm install
cp .env.example .env        # fill in Supabase + Azure OpenAI
make migrate                # apply migrations 001 → 010
make report PILLAR=CYBERSECURITY
make verify REPORT=<uuid>
make pdf    REPORT=<uuid>   # → out/report.pdf
make web                    # console on :3000
```

`make help` lists every target.

## Layout

```
pipeline/            the whole pipeline; every script runs from the repo root
  collect.py         3-lane collector CLI      collectors/  lane A/B/C + registry
  decisions.py       Jev Gate 3 (same-fact merge)
  extract.py         documents → typed evidence
  rules.py           the symbolic layer
  synthesize.py      evidence → signals/findings/risks, by admission rule
  generate.py        bounded drafting + retry-on-verification-failure
  verify.py          citation / gate / class / entailment audit
  export_html.py     report → standalone HTML (design/templates/report.html)
  llm.py             the only place the pipeline talks to a model
  labels.py          enum → reader-facing label      layers.py  UAE layer rules
web/                 Next.js console (no Tailwind, no UI libraries)
supabase/migrations/ 001 → 010, applied in order
design/mockups/      UI reference    design/templates/  report render template
docs/source/         client inputs   docs/design-history/  superseded explorations
out/                 generated reports and PDFs (gitignored)
```

## The three collection lanes

**Lane A — scheduled.** RSS + scrape on a daily cron. When an article page is
blocked, soft-404s, or renders as a JS stub, it falls back to the feed's own
summary rather than losing a Tier-1 item.

**Lane B — question-driven.** Never scheduled: research starts from a strategic
question. GDELT rejects unquoted hyphens and reports errors with HTTP 200, so
queries are built and parsed defensively, spaced ≥5s with escalating backoff.

**Lane C — structured.** MITRE ATT&CK STIX and NVD load straight into `entities`
with no LLM in the path, but still write a document + evidence row so provenance
is unbroken.

`--url ... --depth 1` ingests specific documents and follows policy/PDF links one
level down — how the UAE Tier-1 layer was collected.

### Tier integrity
A document is stored against its **actual publisher's** registry row, not the
aggregator's; `SRC-API-001` is used only when a domain matches nothing. Matching
is most-specific-wins, so `services.nvd.nist.gov` binds to NVD rather than a
broader `nist.gov` row. Tier decides evidence class downstream, so this is not
bookkeeping.

### Sources reached by search, or not at all
NATO NCIA (403 site-wide) and the UAE Cyber Security Council (TLS handshake
fails) are registered as `search` rows. Janes, Shephard and the trade-show
dailies are paywalled and deliberately not seeded. Unreachable sources are
written to `research_gaps` with a reason rather than silently returning nothing.

## Security

- The **anon** key is SELECT-only on every table (migration 010). No anon
  INSERT/UPDATE/DELETE policy exists anywhere.
- The **service** key bypasses RLS and is used by the pipeline and
  `/api/generate` only. It must never carry a `NEXT_PUBLIC_` prefix.
- `/api/ask` answers strictly from stored rows and treats evidence text as data,
  never as instructions.

## Operations

`.github/workflows/collect.yml` runs Lane A daily across four pillars and Lane C
weekly. `.github/workflows/pipeline.yml` is dispatched by the console: it runs
the full chain and reports each stage into `pipeline_runs`, so `/generate`
reflects what actually ran. Without `GH_TOKEN`/`GH_REPO` a requested run stays
`QUEUED` — the system never reports progress that did not happen.

## Known limits

- Citation faithfulness sits around 0.55 on `gpt-4o`; it over-attributes. A
  stronger deployment is the single highest-leverage change available.
- Report sections log `UNSCOPED` — no rows are linked to sections yet, so each
  section receives the whole pillar. The ledger records this rather than
  claiming otherwise.
- `extract.py` assigns `topic_id` round-robin rather than semantically.
- Jev Gates 1 and 2 (relevance triage, quote entailment) are not implemented.
- `/api/ask` still calls Anthropic while the pipeline runs on Azure OpenAI; the
  deterministic path is unaffected.
