"""Environment-layer resolution — deterministic, not a model judgement.

"Middle East, Gulf or UAE targeting" is REGIONAL evidence. Tagging it UAE lets
regional analysis masquerade as national analysis, which is precisely the
inference the validation gate exists to stop. The layer is therefore decided by
what the verbatim quote span actually names, not by what the extractor felt.
"""
from __future__ import annotations

import re

# The UAE, its emirates, and unambiguous national institutions.
UAE_TERMS = [
    r"\bU\.?A\.?E\.?\b", r"\bunited arab emirates\b", r"\bemirati\b", r"\bemirates\b",
    r"\babu dhabi\b", r"\bdubai\b", r"\bsharjah\b", r"\bajman\b", r"\bfujairah\b",
    r"\bras al[- ]khaimah\b", r"\bumm al[- ]quwain\b",
    r"\btawazun\b", r"\baecert\b", r"\btdra\b", r"\bedge group\b",
    r"\bcyber security council\b",
]
UAE_PATTERN = re.compile("|".join(UAE_TERMS), re.I)

# Named on their own, these are regional — never national.
REGIONAL_ONLY = re.compile(
    r"\bmiddle east\b|\bgulf\b|\bgcc\b|\bregion(al)?\b|\barab world\b", re.I)


# Text that may sit between two items of a list and nothing more.
_CONNECTOR = re.compile(r"^[\s,;/&]*(?:or|and|the|as well as)?[\s,;/&]*$", re.I)
_ENUM_WINDOW = 28          # characters; an enumeration keeps its items close


def enumerated_with_region(text: str) -> bool:
    """True when the UAE is named only as one item of a regional list.

    "Middle East, Gulf or UAE targeting" names the UAE, but asserts nothing
    about it specifically — the subject is the region. Treating that as
    UAE-layer evidence is the exact inference the validation gate blocks.
    """
    if not text:
        return False
    for u in UAE_PATTERN.finditer(text):
        for r in REGIONAL_ONLY.finditer(text):
            first, second = sorted([(u.start(), u.end()), (r.start(), r.end())])
            between = text[first[1]:second[0]]
            if len(between) <= _ENUM_WINDOW and _CONNECTOR.match(between):
                return True
    return False


def names_uae(text: str) -> bool:
    """True when the text names the UAE as a subject in its own right."""
    if not text or not UAE_PATTERN.search(text):
        return False
    return not enumerated_with_region(text)


def resolve_env_layer(quote_span: str, proposed: str) -> tuple:
    """Return (layer, changed, reason).

    Downgrades UAE -> REGIONAL when the quote names only a region, and never
    upgrades: an extractor that missed a UAE mention is a smaller problem than
    one that invents national relevance.
    """
    proposed = (proposed or "GLOBAL").upper()
    if proposed != "UAE":
        return proposed, False, ""
    if names_uae(quote_span):
        return "UAE", False, ""
    if enumerated_with_region(quote_span):
        return "REGIONAL", True, "UAE named only within a regional list"
    if REGIONAL_ONLY.search(quote_span or ""):
        return "REGIONAL", True, "quote names a region, not the UAE"
    return "REGIONAL", True, "quote does not name the UAE or an Emirate"
