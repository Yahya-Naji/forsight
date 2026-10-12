"""synthesize.py's admission contract, pinned without a database or a model.

The model proposes signals, findings and risks; these rules decide what enters
the graph. A signal needs two independent publishers, a finding must assert
something falsifiable and rest on at least one Class A/B row, and ids are never
reissued over a citation an old report still carries.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from synthesize import (CITED_ID, IdMinter, _is_platitude,  # noqa: E402
                        finding_admission, risk_score, signal_admission)

SOURCES = {
    "EV-1": [("doc-1", "PUB-A")],
    "EV-2": [("doc-1", "PUB-A")],      # same article as EV-1
    "EV-3": [("doc-2", "PUB-A")],      # same publisher, another article
    "EV-4": [("doc-3", "PUB-B")],
    "EV-5": [("doc-4", None)],         # publisher unresolved
}
VALID = set(SOURCES)

FALSIFIABLE = "GNSS spoofing in the Gulf outpaces civil aviation's published mitigations."
PLATITUDE = "Electronic protection is critical for the UAE."


def test_signal_needs_two_publishers():
    assert signal_admission(["EV-1", "EV-4"], VALID, SOURCES)[1] is None
    # two claims from one article: one source
    assert "publisher" in signal_admission(["EV-1", "EV-2"], VALID, SOURCES)[1]
    # two articles from one publisher: still one source
    assert "publisher" in signal_admission(["EV-1", "EV-3"], VALID, SOURCES)[1]
    # an unresolved publisher is not a second publisher
    assert "publisher" in signal_admission(["EV-1", "EV-5"], VALID, SOURCES)[1]


def test_signal_ignores_invented_and_repeated_ids():
    cited, reason = signal_admission(["EV-1", "EV-1", "EV-404"], VALID, SOURCES)
    assert cited == ["EV-1"] and "evidence row" in reason


def test_finding_rules_in_order():
    assert finding_admission(FALSIFIABLE, [], ["A"])[0] == "finding_admission"
    assert finding_admission(PLATITUDE, ["SIG-1"], ["A"])[0] == "finding_substance"
    assert finding_admission(FALSIFIABLE, ["SIG-1"], ["C", "C"])[0] == "finding_class"
    assert finding_admission(FALSIFIABLE, ["SIG-1"], ["C", "D"])[0] == "finding_class"
    assert finding_admission(FALSIFIABLE, ["SIG-1"], []) [0] == "finding_class"
    assert finding_admission(FALSIFIABLE, ["SIG-1"], ["C", "A"]) is None
    assert finding_admission(FALSIFIABLE, ["SIG-1"], ["B"]) is None


def test_platitudes_are_rejected():
    for text in (PLATITUDE,
                 "Organisations must prioritise robust anti-jam measures.",
                 "Spectrum management is a topic for the UAE."):
        assert _is_platitude(text)[0], text
    for text in (FALSIFIABLE,
                 "Fibre-optic control means RF jamming no longer covers every drone class.",
                 "Software-defined EW shifts lock-in from hardware to threat libraries."):
        assert not _is_platitude(text)[0], text


def test_risk_score():
    by_id = {"E1": {"class": "A", "topic_id": "T1"}, "E2": {"class": "B", "topic_id": "T2"},
             "E3": {"class": "C", "topic_id": "T3"}, "E4": {"class": "C", "topic_id": "T1"}}
    assert risk_score({"E1", "E2", "E3"}, by_id)[:2] == (3, 3)
    assert risk_score({"E1", "E4"}, by_id)[:2] == (2, 1)
    assert risk_score({"E3", "E4"}, by_id)[:2] == (1, 2)


class _FakeTable:
    def __init__(self, rows): self.rows = rows
    def select(self, *_): return self
    def range(self, start, end): return _Page(self.rows[start:end + 1])


class _Page:
    def __init__(self, data): self.data = data
    def execute(self): return self


class _FakeDB:
    def __init__(self, tables): self.tables = tables
    def table(self, name): return _FakeTable(self.tables.get(name, []))


def test_ids_are_never_reissued():
    """After --replace clears the pillar, a report still cites SIG-CS-12; the
    next signal must not be SIG-CS-01 or SIG-CS-12."""
    db = _FakeDB({"signals": [{"id": "SIG-CS-03"}],
                  "reports": [{"body_md": "as shown [SIG-CS-12] and [F-CS-07]"}]})
    m = IdMinter(db)
    assert m.next("SIG-CS-") == "SIG-CS-13"
    assert m.next("SIG-CS-") == "SIG-CS-14"
    assert m.next("F-CS-") == "F-CS-08"
    assert m.next("SIG-EW-") == "SIG-EW-01"
    assert CITED_ID.findall("CU-AI-04 and R-PR-11") == [("CU-AI-", "04"), ("R-PR-", "11")]


def test_branch_clears_only_what_loses_all_support():
    from synthesize import derived_only_from
    links = [("SIG-1", "TR-1"), ("SIG-2", "TR-1"),     # TR-1 also rests on SIG-2
             ("SIG-1", "F-1"),                          # F-1 rests only on SIG-1
             ("SIG-3", "F-2")]
    assert derived_only_from(links, {"SIG-1"}) == {"F-1"}
    assert derived_only_from(links, {"SIG-1", "SIG-2"}) == {"TR-1", "F-1"}
    assert derived_only_from(links, set()) == set()


def test_findings_resolve_signals_by_key():
    """A finding citing S1 reaches the signal admitted from proposal S1 in the
    same response — the model never has to retype a statement."""
    from collections import defaultdict
    from synthesize import SignalProposal, Writer, _resolve, _signal_lookup, admit_signals
    rows = [{"id": e} for e in ("EV-1", "EV-4")]
    w = Writer(None, "ELECTRONIC_WARFARE", dry_run=True)
    minter = IdMinter(_FakeDB({}))
    prop = SignalProposal(key="S1", statement="Gulf GNSS spoofing reports rose across two publishers.",
                          evidence_ids=["EV-1", "EV-4"], direction="STRENGTHENING",
                          env_layer="REGIONAL", steep=["Technological"])
    admitted = admit_signals(w, minter, [prop], rows, SOURCES, defaultdict(list))
    lookup = _signal_lookup([], admitted)
    assert _resolve(lookup, ["S1"]) == ["SIG-EW-01"]
    assert _resolve(lookup, ["S9"]) == []


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("  ✅", t.__name__)
    print("\n✅ %d synthesis contracts hold" % len(tests))
