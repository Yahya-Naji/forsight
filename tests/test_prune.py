"""Sentence-level pruning: when retries run out, the sentences that failed are
cut and the rest of the section is kept. These pin which sentences are found,
and that cutting them leaves clean markdown — no orphan bullets, no doubled
spaces, no space before a full stop."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
import verify
from generate import remove_sentences

GRAPH = {"EV-1": {"claim": "x"}, "EV-2": {"claim": "y"}}

SECTION = """Jamming incidents rose around Gulf airports in 2026 [EV-1]. Iranian drones were downed at a rate of 85 percent across the region last year. Detection ranges grew [EV-2].

- Fibre-optic drones defeat RF jamming entirely [EV-9].
- Layered defence combines sensors and effectors [EV-1]."""


def test_finds_unresolved_and_unsourced():
    bad = verify.failing_sentences(SECTION, GRAPH)
    assert any("EV-9" in b for b in bad), bad                       # cites an id not in the graph
    assert any("85 percent" in b for b in bad), bad                 # a fact with no citation
    assert not any("EV-1]." in b and "Jamming" in b for b in bad), bad


def test_removal_is_clean():
    bad = verify.failing_sentences(SECTION, GRAPH)
    out = remove_sentences(SECTION, bad)
    assert "85 percent" not in out and "EV-9" not in out
    assert "Jamming incidents rose" in out and "Detection ranges grew" in out
    assert "Layered defence" in out
    assert "  " not in out and " ." not in out
    assert not any(l.strip() in ("-", "*") for l in out.splitlines()), out
    assert not verify.failing_sentences(out, GRAPH)


if __name__ == "__main__":
    test_finds_unresolved_and_unsourced(); test_removal_is_clean()
    print("✅ failing sentences found and cut cleanly")
