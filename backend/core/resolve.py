"""
Step one: turn what someone typed into a molecule.

A commercial user types a brand. They type Vymada, not "sacubitril +
valsartan" — the brand is what appears on a prescription, in a tender and in a
competitor's field-force briefing. Until this existed, typing Vymada resolved
to nothing at all, while the catalogue held it under key_brands the whole time.

Four things can come back, and they are different answers:

    molecule    the query names a molecule directly
    brand       the query names a brand of a known molecule
    ambiguous   the brand or fragment maps to more than one molecule
    unknown     nothing matched

Ambiguity is returned, never resolved by picking the first. A brand shared
across molecules, or a fragment like "insulin", has no single right answer, and
choosing silently would attach one molecule's price and evidence to another's
name.

Combination products are matched on any component, so "valsartan" reaches both
Valsartan and Sacubitril + Valsartan. Both are returned rather than ranked,
because which one the user meant is not knowable from the string.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Splits a brand list. Mirrors india_market.SEPARATORS — a joint venture is
# written "Serdia/Servier" and a brand list "Vymada, Azmarda".
BRAND_SPLIT = re.compile(r"\s*[,;/]\s*|\s+&\s+")
# Text in a brand list that names no brand.
NOT_A_BRAND = re.compile(r"^(generics?|various|multiple|others?|many|several|"
                         r"na|n/?a|not available|unknown|-+)$", re.IGNORECASE)
# A combination is written "Sacubitril + Valsartan".
COMPONENT_SPLIT = re.compile(r"\s*\+\s*")


@dataclass
class Match:
    molecule: str
    matched_on: str                 # "molecule" | "brand" | "component"
    matched_text: str
    brands: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class Resolution:
    query: str
    kind: str                       # molecule | brand | ambiguous | unknown
    matches: List[Match] = field(default_factory=list)
    note: Optional[str] = None

    @property
    def molecule(self) -> Optional[str]:
        """The single molecule, or None when there is not exactly one."""
        return self.matches[0].molecule if len(self.matches) == 1 else None

    def to_dict(self) -> Dict[str, Any]:
        return {"query": self.query, "kind": self.kind, "note": self.note,
                "molecule": self.molecule,
                "matches": [m.to_dict() for m in self.matches]}


def parse_brands(text: Optional[str]) -> List[str]:
    if not text:
        return []
    out = []
    for part in BRAND_SPLIT.split(str(text)):
        part = part.strip(" .")
        if part and not NOT_A_BRAND.match(part) and part not in out:
            out.append(part)
    return out


def components(molecule: str) -> List[str]:
    """Components of a combination product, or the molecule itself."""
    return [c.strip() for c in COMPONENT_SPLIT.split(molecule or "") if c.strip()]


def build_index(drugs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Index the catalogue once; resolution is then a dictionary lookup.

    Keys are lowercased. A brand shared by two molecules keeps both, so the
    ambiguity survives to the caller instead of being lost at index time.
    """
    by_molecule: Dict[str, str] = {}
    by_brand: Dict[str, List[str]] = {}
    by_component: Dict[str, List[str]] = {}
    brands_of: Dict[str, List[str]] = {}

    for d in drugs:
        name = (d.get("name") or "").strip()
        if not name:
            continue
        by_molecule[name.lower()] = name
        brands = parse_brands(d.get("key_brands"))
        brands_of[name] = brands
        for b in brands:
            by_brand.setdefault(b.lower(), [])
            if name not in by_brand[b.lower()]:
                by_brand[b.lower()].append(name)
        for c in components(name):
            key = c.lower()
            by_component.setdefault(key, [])
            if name not in by_component[key]:
                by_component[key].append(name)

    return {"by_molecule": by_molecule, "by_brand": by_brand,
            "by_component": by_component, "brands_of": brands_of}


def resolve(query: Optional[str], index: Dict[str, Any]) -> Resolution:
    """What did the user mean? Molecule first, then brand, then component."""
    q = (query or "").strip()
    if not q:
        return Resolution(query=q or "", kind="unknown",
                          note="Nothing entered.")
    key = q.lower()
    brands_of = index.get("brands_of", {})

    exact = index["by_molecule"].get(key)
    if exact:
        return Resolution(query=q, kind="molecule", matches=[
            Match(exact, "molecule", q, brands_of.get(exact, []))])

    hits = index["by_brand"].get(key)
    if hits:
        matches = [Match(m, "brand", q, brands_of.get(m, [])) for m in hits]
        if len(matches) == 1:
            return Resolution(query=q, kind="brand", matches=matches,
                              note=f"'{q}' is a brand of {matches[0].molecule}.")
        return Resolution(query=q, kind="ambiguous", matches=matches,
                          note=f"'{q}' is a brand of more than one molecule "
                               f"({', '.join(m.molecule for m in matches)}). "
                               f"Not resolved — pick one.")

    hits = index["by_component"].get(key)
    if hits:
        matches = [Match(m, "component", q, brands_of.get(m, [])) for m in hits]
        if len(matches) == 1:
            return Resolution(query=q, kind="molecule", matches=matches)
        return Resolution(query=q, kind="ambiguous", matches=matches,
                          note=f"'{q}' is a component of {len(matches)} products "
                               f"({', '.join(m.molecule for m in matches)}). "
                               f"Not resolved — pick one.")

    return Resolution(query=q, kind="unknown", note=(
        f"'{q}' matched no molecule or brand in the catalogue. That is not "
        f"evidence it does not exist — the catalogue is a cache, not the "
        f"universe of drugs."))
