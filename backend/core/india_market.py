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


def from_cdsco_permissions(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Firms holding a CDSCO permission for this molecule.

    Better evidence than the catalogue's key_brands list, which is curated:
    these are named permissions with dates and reference numbers. Manufacture
    permissions are the competition signal — a molecule ten Indian companies
    are permitted to make is contested here whatever its patent status is
    elsewhere. Import permissions describe how it entered, not who competes.
    """
    makers, importers, dates = set(), set(), []
    for r in rows:
        firm = (r.get("firm") or "").strip()
        if not firm:
            continue
        (makers if r.get("permission_type") == "manufacture" else importers).add(firm)
        if r.get("permission_date"):
            dates.append(r["permission_date"])
    return {
        "manufacture_firms": sorted(makers),
        "import_firms": sorted(importers),
        "manufacture_count": len(makers),
        "import_count": len(importers),
        "earliest_permission": min(dates) if dates else None,
        "permission_rows": len(rows),
    }


def india_market(drug: Dict[str, Any],
                 cdsco_permissions: Optional[List[Dict[str, Any]]] = None
                 ) -> Dict[str, Any]:
    """Brands, makers and what they say about competition here.

    CDSCO permissions, where we have them, outrank the catalogue's curated
    brand list — they are named, dated and numbered rather than a selection of
    brands worth knowing.
    """
    brands = parse_list(drug.get("key_brands"))
    makers = parse_list(drug.get("manufacturers"))
    implies_more = brands["implies_more"] or makers["implies_more"]

    permissions = from_cdsco_permissions(cdsco_permissions or [])
    # CDSCO is better EVIDENCE than the curated brand list — named, dated,
    # numbered permissions — but it is not more COMPLETE. The consolidated
    # r-DNA file lists one manufacturer for tenecteplase; a monthly file from
    # the same register names another, and the catalogue names a third. Letting
    # CDSCO override therefore turned a contested molecule into a single-brand
    # one. Both sources are floors, so the higher floor wins and "further
    # makers implied" survives from either.
    state = classify_competition(
        max(len(brands["named"]), permissions["manufacture_count"]),
        max(len(makers["named"]), permissions["manufacture_count"]),
        implies_more)

    if permissions["manufacture_count"]:
        note = (f"{permissions['manufacture_count']} Indian firm(s) hold a CDSCO "
                f"permission to manufacture and market this molecule"
                + (f", the earliest dated {permissions['earliest_permission']}"
                   if permissions["earliest_permission"] else "")
                + ". Named permissions, not a curated brand list.")
    elif state is None:
        note = ("No Indian brands, makers or CDSCO permissions recorded — "
                "competition here is unknown. This is not evidence the molecule "
                "is uncontested; the r-DNA register covers biologicals only and "
                "the new-drug lists miss anything cleared by import permission.")
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
        "cdsco": permissions if permissions["permission_rows"] else None,
        "evidence": ("CDSCO permissions" if permissions["manufacture_count"]
                     else "catalogue key brands"),
        "source_name": ("CDSCO r-DNA register" if permissions["manufacture_count"]
                        else "DROP Tax catalogue (key brands and manufacturers)"),
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
