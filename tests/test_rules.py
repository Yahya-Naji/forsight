"""The symbolic layer's contract, pinned without a database.

rules.py is the only place class, strength and gate status are decided, and the
whole system's claim is that these are computed from provenance rather than
proposed by a model. Each rule is a pure function; these cases fix its
boundaries and, above all, its independence rule: rows and documents from one
publisher never count as corroboration.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from rules import (classify, forced_direction, provenance, signal_strength,  # noqa: E402
                   uae_gate_satisfied)

TIERS = {"PUB-T1": 1, "PUB-T2": 2, "PUB-T4a": 4, "PUB-T4b": 4}
SOURCES = {
    "EV-live-1": [("doc-1", "PUB-T2")],
    "EV-live-2": [("doc-2", "PUB-T2")],          # same publisher, second document
    "EV-archived": [("doc-3", "PUB-T1")],        # retired source
    "EV-aggregator": [("doc-4", None)],          # no publisher resolved
}
LIVE = {"EV-live-1", "EV-live-2", "EV-aggregator"}

# (tiers of the publishers behind the row, distinct publishers) -> (class, confidence)
CLASSIFY = [
    ([1],       1, ("A", "HIGH")),          # one Tier-1 publisher is authoritative
    ([1, 4],    2, ("A", "HIGH")),          # Tier 1 wins over corroboration
    ([2, 3],    2, ("B", "MEDIUM_HIGH")),   # two independent publishers
    ([4, 4],    2, ("B", "MEDIUM_HIGH")),   # two independent Tier-4 publishers still corroborate
    ([2, 2],    1, ("C", "MEDIUM")),        # two documents, ONE publisher: not Class B
    ([2],       1, ("C", "MEDIUM")),
    ([3],       1, ("C", "MEDIUM")),
    ([4],       1, ("C", "LOW")),           # lone Tier 4 is a weak-signal hold
    ([4, 4, 4], 1, ("C", "LOW")),           # three articles from one outlet are one source
    ([],        0, ("C", "LOW")),           # unknown provenance is never promoted
]

# (distinct publishers, any Tier 1) -> strength
STRENGTH = [
    (0, False, "WEAK"),
    (1, False, "WEAK"),
    (1, True,  "WEAK"),              # one Tier-1 publisher is still one publisher
    (2, False, "EMERGING"),
    (2, True,  "STRONG_EMERGING"),
    (3, False, "STRONG"),
    (5, True,  "STRONG"),
]

# (distinct publishers, tiers) -> forced direction or None
DIRECTION = [
    (1, [4],       "UNCERTAIN"),     # one outlet's framing is not a trend
    (1, [4, 4, 4], "UNCERTAIN"),     # nor is the same outlet three times
    (1, [3],       None),
    (2, [4, 4],    None),            # two Tier-4 publishers may carry a direction
    (0, [],        None),
]

# (UAE Class A/B rows, distinct publishers) -> gate satisfied
UAE_GATE = [
    (0, 0, False),
    (1, 1, False),                   # one row, however well sourced, is a data point
    (5, 1, False),                   # many rows from one publisher are one source
    (2, 2, True),
    (6, 3, True),
]


def test_classify():
    wrong = [(t, n, want, classify(t, n)) for t, n, want in CLASSIFY if classify(t, n) != want]
    assert not wrong, "classify: %s" % wrong


def test_signal_strength():
    wrong = [(n, t1, want, signal_strength(n, t1))
             for n, t1, want in STRENGTH if signal_strength(n, t1) != want]
    assert not wrong, "signal_strength: %s" % wrong


def test_forced_direction():
    wrong = [(n, t, want, forced_direction(n, t))
             for n, t, want in DIRECTION if forced_direction(n, t) != want]
    assert not wrong, "forced_direction: %s" % wrong


def test_uae_gate():
    wrong = [(r, p, want) for r, p, want in UAE_GATE if uae_gate_satisfied(r, p) != want]
    assert not wrong, "uae_gate_satisfied: %s" % wrong


def test_archived_evidence_does_not_count():
    """A retired source must not keep a signal strong."""
    evs = ["EV-live-1", "EV-archived"]
    _, pubs, tiers = provenance(evs, SOURCES, TIERS, LIVE)
    assert pubs == {"PUB-T2"} and 1 not in tiers
    assert signal_strength(len(pubs), 1 in tiers) == "WEAK"
    # without the live filter the archived Tier-1 source would have lifted it
    _, pubs_all, tiers_all = provenance(evs, SOURCES, TIERS)
    assert signal_strength(len(pubs_all), 1 in tiers_all) == "STRONG_EMERGING"


def test_provenance_counts_publishers_not_documents():
    docs, pubs, _ = provenance(["EV-live-1", "EV-live-2"], SOURCES, TIERS, LIVE)
    assert len(docs) == 2 and pubs == {"PUB-T2"}
    docs, pubs, _ = provenance(["EV-aggregator"], SOURCES, TIERS, LIVE)
    assert len(docs) == 1 and not pubs          # an unresolved publisher is not a publisher


def test_independence_never_comes_from_one_publisher():
    """The central invariant, across every rule at once: no number of rows or
    documents from a single publisher raises class, strength or the gate."""
    for rows in (1, 2, 5, 50):
        for tier in (2, 3, 4):
            assert classify([tier] * rows, 1)[0] == "C"
            assert signal_strength(1, False) == "WEAK"
            assert not uae_gate_satisfied(rows, 1)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("  ✅", t.__name__)
    print("\n✅ %d rule contracts hold" % len(tests))
