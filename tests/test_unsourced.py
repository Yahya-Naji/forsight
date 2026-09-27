"""The unsourced check is the system's headline claim — 0 unsourced assertions
against 121 in the human benchmark. Every exemption added to it is a chance to
quietly void that number, so each one is pinned here.

MUST_FAIL are claims about the world. MUST_PASS are structure, recommendations,
monitoring conditions, and statements about this document's own coverage — none
of which have an external source to cite.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
import verify

MUST_FAIL = [
    "Iranian state-linked actors have targeted UAE defence suppliers since 2023.",
    "The UAE operates the largest drone defence programme in the Gulf region.",
    "Supply chain attacks increased by forty percent across the sector last year.",
    "So what: Iranian actors have compromised three UAE primes.",
    "This report shows attackers breached the Tawazun supplier portal.",
    "**Bold text that also asserts** that two primes were breached last quarter.",
    "Procurement lead times grew to eighteen months across the sector.",
    "3. **Context**: Two UAE primes were breached in the last quarter.",
    "The falsifier was triggered and two UAE primes were breached last quarter.",
    "Such planning is necessary to address the longer lead time for migration.",
]

MUST_PASS = [
    "**Attackers Demonstrate Capability and Intent to Exploit Supply Chains**",
    "So what: Ensure suppliers are held to stringent cybersecurity standards.",
    "Trigger: Observed increase in cyber resilience gaps across tier-two suppliers.",
    "Falsifier: No UAE prime reports a supplier-origin incident within 24 months.",
    "Two claims are blocked by an open gate and are excluded from this assessment.",
    "The evidence base does not establish a UAE-specific exploitation rate.",
    "Attackers may target internet-exposed edge devices [EV-001].",
    "Mandate cyber-assurance clauses in all tier-one supplier contracts.",
    "4. **Enhance infrastructure readiness**: Address gaps in supplier tooling.",
    "**Revisit**: If vulnerabilities prove incapable of contractual mitigation.",
    "- **Owner**: Assign the procurement authority as accountable party.",
    "Mandate clauses now. Trigger: Increased incidents linked to supplier tooling.",
    "Launch supplier training programmes on advanced threat mitigation.",
    "The falsifier is an adoption rate below 50% among UAE government entities.",
    "The falsifier is the absence of operational digital identity systems by 2027.",
    "What would refute this: no UAE prime reports a supplier-origin incident.",
    "However, if migration slips past 2030, the exposure falls on legacy systems.",
    "Finalize and enforce implementation guidelines for zero-trust architecture.",
    "Reassess if no operational digital identity systems are fielded by 2027.",
]


def _unsourced(text):
    return bool(verify.check_unsourced(verify.sentences_of(text)))


def test_real_claims_are_caught():
    leaks = [s for s in MUST_FAIL if not _unsourced(s)]
    assert not leaks, "unsourced claims slipped through: %s" % leaks


def test_structure_is_not_a_claim():
    wrong = [s for s in MUST_PASS if _unsourced(s)]
    assert not wrong, "false positives on non-claims: %s" % wrong


if __name__ == "__main__":
    for s in MUST_FAIL:
        print(("  ✅" if _unsourced(s) else "  ❌ LEAK") + "  " + s[:70])
    print()
    for s in MUST_PASS:
        print(("  ✅" if not _unsourced(s) else "  ❌ FALSE POS") + "  " + s[:70])
    test_real_claims_are_caught(); test_structure_is_not_a_claim()
    print("\n✅ both directions hold")
