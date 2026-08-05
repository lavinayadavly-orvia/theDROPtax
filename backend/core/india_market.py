"""
The Indian competitive picture — brands and makers, not patents.

"Exclusivity" is a United States concept and it does not describe this market.
India has no patent linkage, Section 3(d) blocks evergreening, compulsory
licensing exists, and price control applies only to NLEM formulations. Branded
generics are the default rather than the exception, and a molecule can carry
dozens of brands while the same molecule is still exclusive elsewhere.

Drugs@FDA said tenecteplase was exclusive to Genentech with zero generic
sponsors, so the classifier printed "No generic competition — the originator
sets the price." The same record holds brands Elaxim and Tenectase, made by
Emcure. That statement was false for the market the platform serves.

So the Indian question is not "has exclusivity expired" but "how many brands
are marketed, by how many companies". That is what erodes price here.

A floor, not a count
--------------------
key_brands lists the brands worth knowing, not every brand on the market.
Ramipril carries three here and far more in reality. Every count from this
module is therefore a LOWER BOUND, and says so, because reporting "3 brands"
for a molecule with forty would understate competition exactly where it
matters.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Splits a free-text brand or maker list. Slash is included because the
# workbook writes joint ventures as "Serdia/Servier".
SEPARATORS = re.compile(r"\s*[,;/]\s*|\s+&\s+|\s+\band\b\s+", re.IGNORECASE)
# Text that names no specific company.
VAGUE = re.compile(r"^(generics?|various|multiple|others?|many|several|na|n/?a|"
                   r"not available|unknown|-+)$", re.IGNORECASE)

MANY_BRANDS = 5


def parse_list(text: Optional[str]) -> Dict[str, Any]:
    """Split a free-text list, separating named entries from vague ones.

    "Emcure, generics" names one company and asserts there are more. Both
    facts are kept: the named one can be counted, the vague one cannot, and
    dropping it would lose the information that others exist.
    """
    if not text or not str(text).strip():
        return {"named": [], "implies_more": False}
    named, implies_more = [], False
    for part in SEPARATORS.split(str(text)):
        part = part.strip(" .")
        if not part:
            continue
        if VAGUE.match(part):
            implies_more = True
            continue
        if part not in named:
            named.append(part)
    return {"named": named, "implies_more": implies_more}


def classify_competition(brand_count: int, maker_count: int,
                         implies_more: bool) -> Optional[str]:
    """How contested the molecule is in India, on the evidence we hold."""
    n = max(brand_count, maker_count)
    if n == 0:
        return None
    if implies_more or n >= MANY_BRANDS:
        return "many_brands"
    if n == 1:
        return "single_brand"
    return "few_brands"


def india_market(drug: Dict[str, Any]) -> Dict[str, Any]:
    """Brands, makers and what they say about competition here."""
    brands = parse_list(drug.get("key_brands"))
    makers = parse_list(drug.get("manufacturers"))
    implies_more = brands["implies_more"] or makers["implies_more"]
    state = classify_competition(len(brands["named"]), len(makers["named"]),
                                 implies_more)

    if state is None:
        note = ("No Indian brands or makers recorded — competition here is "
                "unknown. This is not evidence the molecule is uncontested.")
    elif state == "single_brand":
        note = ("One brand recorded. Where that is the whole market the "
                "originator sets the price, but the list holds key brands "
                "rather than every brand, so treat it as a floor.")
    else:
        more = " and the record indicates further makers" if implies_more else ""
        note = (f"{len(brands['named'])} brand(s) from "
                f"{len(makers['named'])} named maker(s){more}. Branded generics "
                f"compete on price here without any exclusivity having to expire.")

    return {
        "brands": brands["named"],
        "manufacturers": makers["named"],
        "brand_count_floor": len(brands["named"]),
        "manufacturer_count_floor": len(makers["named"]),
        # key_brands is a curated subset, so both counts are lower bounds.
        "counts_are_lower_bounds": True,
        "more_makers_implied": implies_more,
        "competition": state,
        "note": note,
        "source_name": "DROP Tax catalogue (key brands and manufacturers)",
    }


def reconcile_with_us(india: Dict[str, Any],
                      us_exclusivity: Optional[str]) -> Optional[str]:
    """Flag where the US picture would mislead about India.

    Returns a warning when Drugs@FDA says exclusive and Indian brands exist —
    the tenecteplase case, where the US reading produced a false statement.
    """
    if us_exclusivity == "exclusive" and india.get("competition") in (
            "few_brands", "many_brands"):
        makers = ", ".join(india["manufacturers"][:3]) or "Indian makers"
        return (f"US records show no generic competition, but this molecule is "
                f"marketed in India by {makers}. The US position does not "
                f"describe this market and must not be reported as if it did.")
    return None
