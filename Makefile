# Foresight POC — common operations.
# Everything runs from the repo root; no `cd pipeline` required.

PY      ?= .venv/bin/python
PILLAR  ?= CYBERSECURITY
TITLE   ?= $(PILLAR) baseline
REPORT  ?=

.PHONY: help setup migrate collect extract gate3 rules synth forecast generate verify report pdf evaluate web build clean prompts prompts-check dump restore refile refile-apply seed-ew

help:               ## list the available targets
	@grep -E '^[a-z0-9-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/' | expand -t22

setup:              ## create the venv and install Python + web dependencies
	python3 -m venv .venv && $(PY) -m pip install -q -r pipeline/requirements.txt
	cd web && npm install

migrate:            ## apply every SQL migration in order
	$(PY) pipeline/apply_migrations.py

collect:            ## lane A sweep for $(PILLAR)
	$(PY) pipeline/collect.py --lane a --pillar $(PILLAR)

extract:            ## documents -> typed evidence
	$(PY) pipeline/extract.py --pillar $(PILLAR)

gate3:              ## merge same-fact evidence from one document
	$(PY) pipeline/decisions.py --gate 3 --pillar $(PILLAR)

rules:              ## class, confidence, signal strength, gates
	$(PY) pipeline/rules.py

synth:              ## evidence -> signals, findings, risks
	$(PY) pipeline/synthesize.py --pillar $(PILLAR)

forecast:           ## project forward: outlook with computed plausibility
	$(PY) pipeline/forecast.py --pillar $(PILLAR) --replace

generate:           ## draft the report from the graph
	$(PY) pipeline/generate.py --pillar $(PILLAR) --title "$(TITLE)"

verify:             ## audit a report: make verify REPORT=<uuid>
	$(PY) pipeline/verify.py --report $(REPORT)

report: extract gate3 rules synth forecast generate   ## full chain for $(PILLAR)
	@echo "Generated. Verify with: make verify REPORT=<uuid>"

pdf:                ## render a report to HTML + PDF: make pdf REPORT=<uuid>
	$(PY) pipeline/export_html.py --report $(REPORT) --out out/report.html
	"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless \
	  --disable-gpu --no-sandbox --virtual-time-budget=20000 --no-pdf-header-footer \
	  --print-to-pdf="$(PWD)/out/report.pdf" "file://$(PWD)/out/report.html"
	@echo "out/report.pdf"

BENCHMARK ?= docs/source/counter-uas-report-v1.0.docx

evaluate:           ## score against a benchmark: make evaluate BENCHMARK=path.pdf
	$(PY) pipeline/evaluate.py --pillar $(PILLAR) --benchmark "$(BENCHMARK)" \
	  --json out/scorecard.json

prompts:            ## write every agent's prompt to agents/prompts/
	$(PY) pipeline/export_prompts.py

prompts-check:      ## fail if agents/prompts/ is stale against the code
	$(PY) pipeline/export_prompts.py --check

seed-ew:            ## ingest the EW document seed (docs/ew-document-seed.txt) — documents only
	$(PY) pipeline/collect.py --lane a $$(grep -E '^https?://' docs/ew-document-seed.txt | awk '{print "--url " $$1}')

refile:             ## propose EW-core topic placements -> out/refile/*.csv (changes nothing)
	$(PY) pipeline/refile.py

refile-apply:       ## apply a reviewed proposal: make refile-apply FILE=out/refile/<x>.csv
	$(PY) pipeline/refile.py --apply $(FILE)

dump:               ## snapshot Postgres into db/dumps/<stamp>/ (needs Docker)
	./db/dump.sh

restore:            ## restore a snapshot: make restore DB=<postgres-url> [DUMP=db/dumps/<stamp>]
	./db/restore.sh "$(DB)" $(DUMP)

web:                ## run the console locally
	cd web && npm run dev

build:              ## production build of the console
	cd web && npx next build

clean:              ## remove build artefacts and caches
	rm -rf out/* web/.next
	find . -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	find . -name .DS_Store -delete 2>/dev/null || true
