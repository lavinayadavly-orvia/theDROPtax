"""
Turn indication prose into structured indications.

112 of the 218 catalogue rows name more than one indication — 299 in total —
and every one of them was trapped in a single free-text string. Nothing can
branch on a semicolon, so the platform behaved as though each molecule had
exactly one use. It does not: ramipril for hypertension and ramipril for
high cardiovascular risk rest on different trials and answer to different
questions, at the same price.

The unit the platform reasons about is (drug x indication), and this module
produces that unit.

Splitting rules, derived from the data rather than assumed
----------------------------------------------------------
Separators are ';', '|' and ' / '. Commas are NEVER separators: no row in the
catalogue uses one as its only separator, while several carry commas inside
parentheses ("Osteoporosis (Prolia, 6-monthly)"), so splitting on them would
manufacture indications that do not exist.

Parentheses are qualifiers attached to the indication before them, not
indications in their own right — "portal HTN (variceal bleed prophylaxis)" is
one indication with a note, and "high CV-risk (HOPE)" names the trial it rests
on. Text inside them is preserved, never discarded and never promoted.

An indication that does not resolve to the therapy-area registry is kept and
marked unmapped. Dropping it would quietly shrink the drug's real scope, and
forcing it to the nearest registry entry would invent a therapeutic claim.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from core.therapy_areas import resolve_indication, get_category

# ';' carries 121 of the rows; '|' and ' / ' appear rarely but unambiguously.
SEPARATOR = re.compile(r"\s*[;|]\s*|\s+/\s+")
PARENTHETICAL = re.compile(r"\(([^)]*)\)")
OFF_LABEL = re.compile(r"\boff[- ]label\b", re.IGNORECASE)
# "also erectile dysfunction" inside a parenthetical is a second indication
ALSO = re.compile(r"^\s*also\s+(.+)$", re.IGNORECASE)


@dataclass
class Indication:
    """One indication, with what it resolved to and what it did not."""
    text: str                       # display name, e.g. "Heart failure"
    raw: str                        # the fragment as written
    qualifier: Optional[str] = None  # parenthetical note, verbatim
    off_label: bool = False
    registry_indication: Optional[str] = None   # therapy-area registry match
    category: Optional[str] = None
    mapped: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _tidy(fragment: str) -> str:
    fragment = re.sub(r"\s+", " ", fragment).strip(" ,.-–—")
    return fragment


def _display(text: str) -> str:
    """Capitalise for display without touching acronyms (HFrEF, PPH, DUB)."""
    if not text:
        return text
    if text[0].isupper() or text[:4].isupper():
        return text
    return text[0].upper() + text[1:]


def parse(indication_text: Optional[str]) -> List[Indication]:
    """Split an indication string into structured indications.

    Returns [] for empty input rather than a placeholder — a drug with no
    recorded indication is a gap to surface, not an indication named "unknown".
    """
    if not indication_text or not indication_text.strip():
        return []

    out: List[Indication] = []
    for raw_fragment in SEPARATOR.split(indication_text):
        raw_fragment = _tidy(raw_fragment)
        if len(raw_fragment) < 3:
            continue

        # Pull the parenthetical off as a qualifier; it stays attached, and an
        # "also X" inside it is the one case where it names a further indication.
        qualifiers = PARENTHETICAL.findall(raw_fragment)
        body = _tidy(PARENTHETICAL.sub(" ", raw_fragment))
        extra: List[str] = []
        kept: List[str] = []
        for q in qualifiers:
            m = ALSO.match(_tidy(q))
            if m:
                extra.append(_tidy(m.group(1)))
            else:
                kept.append(_tidy(q))

        for text, qual in [(body, "; ".join(kept) or None)] + [(e, None) for e in extra]:
            if len(text) < 3:
                continue
            off_label = bool(OFF_LABEL.search(raw_fragment)) or bool(
                OFF_LABEL.search(qual or ""))
            clean = _tidy(OFF_LABEL.sub("", text))
            if len(clean) < 3:
                continue
            entry = resolve_indication(clean)
            out.append(Indication(
                text=_display(clean),
                raw=raw_fragment,
                qualifier=qual,
                off_label=off_label,
                registry_indication=entry["indication"] if entry else None,
                category=(entry["category"] if entry else None) or (
                    get_category(clean) if entry else None),
                mapped=entry is not None,
            ))
    return out


def structure(indication_text: Optional[str]) -> Dict[str, Any]:
    """Full structured view of a drug's indications.

    The primary indication is the first that resolves to the registry — that is
    the one bringing the drug into scope. If none resolve, the first is used and
    the record says nothing mapped, rather than implying a therapy area we did
    not establish.
    """
    items = parse(indication_text)
    primary = next((i for i in items if i.mapped), items[0] if items else None)
    return {
        "indications": [i.to_dict() for i in items],
        "indication_count": len(items),
        "has_multiple_indications": len(items) > 1,
        "primary_indication": primary.text if primary else None,
        "primary_registry_indication": primary.registry_indication if primary else None,
        "primary_category": primary.category if primary else None,
        "mapped_count": sum(1 for i in items if i.mapped),
        "unmapped": [i.text for i in items if not i.mapped],
        "off_label_count": sum(1 for i in items if i.off_label),
    }
