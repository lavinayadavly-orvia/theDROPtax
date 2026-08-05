"""
Match a molecule to its Indian approval.

Substring matching is not good enough here. Searching the raw row text for
"ramipril" returns a metoprolol-plus-atorvastatin combination, because the
molecule appears somewhere in a long block of prose, and the answer that comes
back is a different product's approval date.

Two rules fix it:

1. Match on the drug-name portion of the row, not the whole row. An indication
   naming a comparator drug is not an approval of that drug.
2. A fixed-dose combination containing the molecule is a real approval, but a
   different fact from the single-molecule approval. Both are returned; the
   single-molecule one is preferred for the first-approval date, and where only
   an FDC exists the record says so instead of implying the molecule was
   approved on its own.

Absence is never approval status. A molecule not in this register reads as
"not found in the CDSCO new-drug lists" — the register begins in the 1960s but
is thin before roughly 2009, and several older lists are scanned images that
have never been read. Tenecteplase is sold in India as Elaxim and does not
appear.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# A combination product names more than one molecule, joined like this.
COMBINATION = re.compile(r"\+|\band\b(?=[^,]*\b(?:tablet|capsule|injection|mg|bulk)\b)",
                         re.IGNORECASE)
# Words that are formulation, not molecule.
FORM_WORDS = re.compile(
    r"\b(bulk drug|bulk|tablets?|capsules?|injections?|solution|suspension|"
    r"film coated|extended release|prolonged release|sustained release|"
    r"oral|iv|sc|im|powder|syrup|drops?|gel|cream|patch|sachet|vial|"
    r"prefilled|syringe|pen|for injection|lyophilised|lyophilized)\b",
    re.IGNORECASE)
# Units survive the digit strip and would otherwise leave "brexpiprazole mg".
UNITS = re.compile(r"\b(mg|mcg|ug|ml|gm|g|iu|meq|mmol|w/v|w/w|v/v)\b", re.IGNORECASE)


def normalise(name: Optional[str]) -> str:
    """Molecule name reduced to comparable form — salts and forms removed."""
    if not name:
        return ""
    s = name.lower()
    s = FORM_WORDS.sub(" ", s)
    # Salt and hydrate suffixes do not change the molecule for this purpose.
    s = re.sub(r"\b(hydrochloride|hcl|sodium|potassium|calcium|maleate|tartrate|"
               r"besylate|mesylate|succinate|fumarate|sulfate|sulphate|acetate|"
               r"citrate|tosylate|monohydrate|dihydrate|anhydrous|micronised|"
               r"micronized)\b", " ", s)
    s = re.sub(r"[^a-z ]+", " ", s)
    s = UNITS.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _mentions(molecule: str, text: str) -> bool:
    """Word-boundary match on the normalised molecule name."""
    if not molecule or not text:
        return False
    return re.search(rf"\b{re.escape(molecule)}\b", text) is not None


def find_approvals(molecule: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Everything the register holds for one molecule.

    `rows` are CDSCO approval records. Matching looks at the drug-name field,
    never the indication — a row whose indication mentions a comparator is not
    an approval of the comparator.
    """
    target = normalise(molecule)
    if not target:
        return _empty(molecule)

    single, combination = [], []
    for r in rows:
        name_norm = normalise(r.get("drug_name"))
        if not _mentions(target, name_norm):
            continue
        raw_name = r.get("drug_name") or ""
        # A row naming several molecules is a combination product.
        others = [w for w in name_norm.split() if len(w) > 6 and w != target]
        is_combo = bool(COMBINATION.search(raw_name)) or len(others) >= 2
        (combination if is_combo else single).append(r)

    if not single and not combination:
        return _empty(molecule)

    preferred = single or combination
    dated = [r for r in preferred if r.get("approval_date")]
    first = min(dated, key=lambda r: r["approval_date"]) if dated else None

    indications = []
    for r in preferred:
        ind = (r.get("indication") or "").strip()
        if ind and ind.lower() not in ("not applicable as it is a bulk drug",) \
                and ind not in indications:
            indications.append(ind[:400])

    return {
        "molecule": molecule,
        "found": True,
        "approved_in_india": True,
        "first_approval_date": first["approval_date"] if first else None,
        "approval_day_known": first.get("approval_day_known") if first else None,
        "single_molecule_rows": len(single),
        "combination_rows": len(combination),
        # Where only a combination exists, the molecule was not approved alone
        # on this evidence, and saying otherwise would be a different claim.
        "only_as_combination": not single and bool(combination),
        "india_indications": indications[:6],
        "source_name": "CDSCO List of Approved New Drugs",
        "source_url": (first or preferred[0]).get("source_url"),
        "source_list": (first or preferred[0]).get("source_list"),
    }


def _empty(molecule: str) -> Dict[str, Any]:
    return {
        "molecule": molecule,
        "found": False,
        # NOT False — absence from the register is not evidence of non-approval.
        "approved_in_india": None,
        "first_approval_date": None,
        "india_indications": [],
        "note": ("Not found in the CDSCO new-drug lists. The register is thin "
                 "before about 2009 and several older lists are scanned images "
                 "that cannot be read, so this is not evidence the molecule is "
                 "unapproved in India."),
        "source_name": "CDSCO List of Approved New Drugs",
    }
