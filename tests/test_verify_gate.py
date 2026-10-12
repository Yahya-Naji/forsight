"""The gate check: a UAE-gap claim is blocked while a gate is open, and a
sentence that merely discloses the gate is not."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from verify import check_gates  # noqa: E402


class _Q:
    def __init__(self, rows): self.rows = rows
    def select(self, *_): return self
    def eq(self, *_): return self
    def execute(self): return self
    @property
    def data(self): return self.rows


class _DB:
    def table(self, _):
        return _Q([{"id": "VG-EL-01", "status": "OPEN",
                    "blocks": "Any UAE-specific capability-gap claim for the Electronic Warfare pillar"}])


DISCLOSURES = [
    "The validation gate relating to the Electronic Warfare pillar indicates that any "
    "UAE-specific capability-gap claims require further validation, which is outstanding.",
    "UAE-specific gap claims require customer validation before they can be stated.",
    "One open gate means UAE capability-gap claims require validation by the customer.",
    "Validation gates are open for any UAE-specific capability-gap claim; this blocks any such claims [VG-EL-01].",
]
GAP_CLAIMS = [
    "The UAE lacks adequate jamming coverage against fibre-optic drones.",
    "Tawazun faces a shortfall in counter-UAS effectors.",
    "The UAE lacks jamming coverage, although the open gate requires validation of such claims.",
    "The UAE is behind on EW reprogramming while the gate stays open.",
]


def test_disclosures_pass():
    flagged = [s for s in DISCLOSURES if check_gates(_DB(), [s], "ELECTRONIC_WARFARE")]
    assert not flagged, flagged


def test_gap_claims_blocked():
    missed = [s for s in GAP_CLAIMS if not check_gates(_DB(), [s], "ELECTRONIC_WARFARE")]
    assert not missed, missed


if __name__ == "__main__":
    test_disclosures_pass(); test_gap_claims_blocked()
    print("✅ gate disclosures pass, gap claims blocked")
