"""Human-readable labels for enum values.

Database enums are SCREAMING_SNAKE because that is what Postgres enums should
be. A reader of a Tawazun brief should never see one. This is the single
mapping; generate.py and the dashboard both use it so they cannot drift.
"""
from __future__ import annotations

PILLAR = {
    "CYBERSECURITY": "Cybersecurity",
    "AI": "Artificial Intelligence",
    "ELECTRONIC_WARFARE": "Electronic Warfare",
    "PROCUREMENT": "Procurement",
}
STRENGTH = {
    "WEAK": "Weak", "EMERGING": "Emerging",
    "STRONG_EMERGING": "Strong-Emerging", "STRONG": "Strong",
}
DIRECTION = {
    "STRENGTHENING": "Strengthening", "UNCERTAIN": "Uncertain",
    "WEAKENING": "Weakening",
}
LAYER = {"UAE": "UAE", "REGIONAL": "Regional", "GLOBAL": "Global"}
CONFIDENCE = {
    "LOW": "Low", "MEDIUM": "Medium",
    "MEDIUM_HIGH": "Medium-High", "HIGH": "High",
}
EVIDENCE_CLASS = {
    "A": "Class A — authoritative fact",
    "B": "Class B — corroborated finding",
    "C": "Class C — foresight hypothesis (unproven)",
    "D": "Class D — proposed construct",
}
GATE = {
    "FETC_REVIEW": "FETC review", "CUSTOMER_VALIDATION": "Customer validation",
    "EXPERT_VALIDATION": "Expert validation",
}
STATUS = {"OPEN": "Open", "PASSED": "Passed", "FAILED": "Failed",
          "WATCHING": "Watching", "THRESHOLD_MET": "Threshold met", "FIRED": "Fired"}
HORIZON = {"H0_3": "0–3 years", "H3_5": "3–5 years",
           "H5_10": "5–10 years", "H7_PLUS": "7+ years"}

_ALL = {}
for _m in (PILLAR, STRENGTH, DIRECTION, LAYER, CONFIDENCE, GATE, STATUS, HORIZON):
    _ALL.update(_m)

# Fields whose values are enums and must be relabelled before the model or a
# reader ever sees them.
ENUM_FIELDS = {"pillar", "strength", "direction", "env_layer", "confidence",
               "gate", "status", "horizon", "planning_horizon"}


def label(value):
    """Map one enum value to its display form; pass anything else through."""
    if isinstance(value, str):
        return _ALL.get(value, value)
    return value


def humanise(obj):
    """Recursively relabel enum-valued fields in rows handed to generation.

    Applied to the JSON payload, so the model never sees a raw enum and cannot
    copy one into prose or a table.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ENUM_FIELDS and isinstance(v, str):
                out[k] = label(v)
            elif k in ENUM_FIELDS and isinstance(v, list):
                out[k] = [label(x) for x in v]
            else:
                out[k] = humanise(v)
        return out
    if isinstance(obj, list):
        return [humanise(x) for x in obj]
    return obj
