"""
Orienting facts — the cheap lookups that decide what else is worth fetching.

Before the platform knows what to show for a drug, it needs to know what kind
of problem the drug is. A 1996 molecule with twenty-five generic sponsors and a
2021 molecule with one are different products commercially, whatever their
labels say, and they warrant different depth.

These facts come from openFDA's Drugs@FDA endpoint at query time, so the answer
does not depend on the molecule being in our catalogue. A user can type anything.

    approval date        earliest approved submission across all applications
    exclusivity          whether any ANDA (generic) application exists
    sponsor count        distinct companies holding approvals

US data, and labelled as such
-----------------------------
Drugs@FDA is a United States register. It establishes US approval and US
genericisation. Indian availability is a different fact with a different
regulator, and the two diverge in both directions — a molecule can be
genericised in India while still exclusive in the US, and CDSCO approval dates
routinely differ from FDA ones by years.

So every field here is named us_*, and nothing infers Indian status from it.
Where the Indian answer is needed, it has to come from CDSCO or the market, and
until it does the honest value is None.
"""
from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

ENDPOINT = "https://api.fda.gov/drug/drugsfda.json"
SOURCE_NAME = "openFDA Drugs@FDA"
SOURCE_URL = "https://open.fda.gov/apis/drug/drugsfda/"
USER_AGENT = "DropTax/1.0 (clinical intelligence platform)"

# Distinct companies holding generic approvals. One sponsor with six ANDAs is
# not a competitive market, so sponsors are counted, not applications.
MANY_MAKERS = 5


@dataclass
class OrientingFacts:
    molecule: str
    us_first_approval: Optional[str] = None        # ISO date
    us_has_generics: Optional[bool] = None
    us_generic_sponsors: Optional[int] = None
    us_total_sponsors: Optional[int] = None
    us_exclusivity: Optional[str] = None           # see classify_exclusivity
    brand_sponsor: Optional[str] = None
    application_count: Optional[int] = None
    found: bool = False
    # India is a separate regulator and stays unknown until sourced separately.
    india_status: None = None
    source_name: str = SOURCE_NAME
    source_url: str = SOURCE_URL
    retrieved: str = field(default_factory=lambda: date.today().isoformat())
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["india_status"] = None
        return d


def classify_exclusivity(generic_sponsors: Optional[int]) -> Optional[str]:
    """Three states, because the middle one behaves unlike either edge.

    A molecule with generics but only one or two makers can hold a high price
    indefinitely — no exclusivity to expire, and no competition to erode it.
    Nothing in the current catalogue sits there, but a user can type any drug.
    """
    if generic_sponsors is None:
        return None
    if generic_sponsors == 0:
        return "exclusive"
    if generic_sponsors < MANY_MAKERS:
        return "generic_few_makers"
    return "generic_many_makers"


def _iso(fda_date: Optional[str]) -> Optional[str]:
    """FDA dates arrive as YYYYMMDD."""
    if not fda_date or len(str(fda_date)) != 8 or not str(fda_date).isdigit():
        return None
    s = str(fda_date)
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def _http_get_json(url: str, timeout: int = 25) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout,
                                context=ssl.create_default_context()) as r:
        return json.loads(r.read())


def fetch(molecule: str, fetch_json=_http_get_json) -> List[Dict[str, Any]]:
    """Applications for a molecule. Empty list when openFDA has none.

    openFDA answers a no-match with HTTP 404, which is a legitimate answer to
    "does this exist", not a failure — it is returned as an empty list so the
    caller reports 'not found in Drugs@FDA' rather than an error.
    """
    query = urllib.parse.quote(f'openfda.generic_name:"{molecule.lower()}"')
    try:
        payload = fetch_json(f"{ENDPOINT}?search={query}&limit=100")
    except Exception:
        return []
    return payload.get("results", []) or []


def summarise(molecule: str, records: List[Dict[str, Any]]) -> OrientingFacts:
    """Derive the orienting facts. Absent input yields None, never a default."""
    if not records:
        return OrientingFacts(
            molecule=molecule, found=False,
            note="Not found in Drugs@FDA — US status unknown. This is not "
                 "evidence the molecule is unapproved elsewhere.")

    generic_sponsors, brand_sponsors, all_sponsors = set(), set(), set()
    approval_dates: List[str] = []
    for r in records:
        number = (r.get("application_number") or "").upper()
        sponsor = (r.get("sponsor_name") or "").strip() or None
        if sponsor:
            all_sponsors.add(sponsor)
            (generic_sponsors if number.startswith("ANDA") else brand_sponsors).add(sponsor)
        for sub in r.get("submissions") or []:
            if sub.get("submission_status") == "AP":
                iso = _iso(sub.get("submission_status_date"))
                if iso:
                    approval_dates.append(iso)

    n_generic = len(generic_sponsors)
    # For old molecules the originator application can be withdrawn or
    # transferred out of the register, leaving only generics. The earliest
    # surviving approval is then a floor, not the true first approval —
    # ramipril reads 2008 in Drugs@FDA and was approved in 1991. Say so rather
    # than let a derived age be trusted as fact.
    note = None
    if approval_dates and not brand_sponsors and n_generic:
        note = ("No originator application in the register — the earliest date "
                "is the oldest surviving generic approval and is a lower bound "
                "on the true first approval, not the date itself.")

    return OrientingFacts(
        molecule=molecule,
        us_first_approval=min(approval_dates) if approval_dates else None,
        us_has_generics=n_generic > 0,
        us_generic_sponsors=n_generic,
        us_total_sponsors=len(all_sponsors) or None,
        us_exclusivity=classify_exclusivity(n_generic),
        brand_sponsor=sorted(brand_sponsors)[0] if brand_sponsors else None,
        application_count=len(records),
        found=True,
        note=note,
    )


def orienting_facts(molecule: str, fetch_json=_http_get_json) -> OrientingFacts:
    """One call: molecule in, orienting facts out, with provenance attached."""
    return summarise(molecule, fetch(molecule, fetch_json=fetch_json))
