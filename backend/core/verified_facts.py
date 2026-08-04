"""
Source-verified drug facts.

Every entry here was read from a named authoritative document, with the URL and
the date it was retrieved. Nothing in this file may be written from memory or
inferred — if a value was not read from the cited source, it does not belong
here and stays absent (the platform then reports it as unavailable).

This overlay takes precedence over the imported workbook, which is a compiled
reference of unverified provenance.

Adding an entry
---------------
1. Open the primary source (FDA/EMA label, CDSCO approval, NPPA price list,
   regulator or manufacturer document — not a summary or a blog).
2. Copy the value exactly as stated.
3. Record `source_name`, `source_url`, `retrieved` (ISO date) and, where the
   wording matters, `quote`.
4. Only fill the fields the document actually supports. Leave the rest out.

Field notes
-----------
`doses_year_1` / `doses_maintenance` express loading-dose regimens, which a
single monthly figure cannot represent. The value engine uses them to derive
year-one and steady-state costs separately.
"""

from typing import Dict, Any, Optional

# Auto-generated from FDA labels via DailyMed (verify_from_dailymed.py).
# Hand-curated entries below take precedence over the generated ones.
try:
    from .verified_facts_dailymed import DAILYMED_FACTS, UNMATCHED as DAILYMED_UNMATCHED
except ImportError:  # generated file not present yet
    DAILYMED_FACTS, DAILYMED_UNMATCHED = {}, []


VERIFIED_FACTS: Dict[str, Dict[str, Any]] = {

    "inclisiran": {
        "molecule": "Inclisiran",
        "facts": {
            "us_initial_approval_year": {
                "value": 2021,
                "source_name": "FDA prescribing information (LEQVIO), via DailyMed",
                "source_url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=6fc0afca-4513-4c35-b594-6544aee29a44",
                "retrieved": "2026-08-03",
                "quote": "Initial U.S. Approval: 2021",
            },
            "dosing_schedule": {
                "value": "284 mg subcutaneously initially, again at 3 months, then every 6 months",
                "doses_year_1": 3,          # month 0, month 3, month 9
                "doses_maintenance": 2,     # every 6 months thereafter
                "source_name": "FDA prescribing information (LEQVIO), via DailyMed",
                "source_url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=6fc0afca-4513-4c35-b594-6544aee29a44",
                "retrieved": "2026-08-03",
                "quote": ("284 mg administered as a single subcutaneous injection initially, "
                          "again at 3 months, and then every 6 months."),
            },
            "strength": {
                "value": "284 mg/1.5 mL (189 mg/mL)",
                "source_name": "FDA prescribing information (LEQVIO), via DailyMed",
                "source_url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=6fc0afca-4513-4c35-b594-6544aee29a44",
                "retrieved": "2026-08-03",
            },
            "manufacturer": {
                "value": "Novartis Pharmaceuticals Corporation",
                "source_name": "FDA prescribing information (LEQVIO), via DailyMed",
                "source_url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=6fc0afca-4513-4c35-b594-6544aee29a44",
                "retrieved": "2026-08-03",
            },
            "indication": {
                "value": ("Reduce LDL-C in adults with hypercholesterolemia; adults and "
                          "patients aged 12+ with HeFH; patients aged 12+ with HoFH"),
                "source_name": "FDA prescribing information (LEQVIO), via DailyMed",
                "source_url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=6fc0afca-4513-4c35-b594-6544aee29a44",
                "retrieved": "2026-08-03",
            },
            "ldl_c_reduction_percent": {
                # Placebo-adjusted mean change in LDL-C at Day 510. Three
                # pivotal trials are reported; each is kept with its own figure
                # rather than averaged into a single synthetic number.
                "value": 52.0,
                "trials": {
                    "ORION-10": {"value": 52.0, "ci": "-56%, -49%", "population": "ASCVD"},
                    "ORION-11": {"value": 50.0, "ci": "-53%, -47%", "population": "ASCVD / ASCVD-risk equivalent"},
                    "ORION-9":  {"value": 48.0, "ci": "-54%, -42%", "population": "HeFH"},
                },
                "headline_trial": "ORION-10",
                "range": "48-52% across ORION-9/10/11",
                "source_name": "FDA prescribing information (LEQVIO), Clinical Studies, via DailyMed",
                "source_url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=6fc0afca-4513-4c35-b594-6544aee29a44",
                "retrieved": "2026-08-03",
                "quote": ("The difference between the LEQVIO and placebo groups in mean percentage "
                          "change in LDL-C from baseline to Day 510 was -52% (95% CI: -56%, -49%; "
                          "p < 0.0001)."),
            },
            "adverse_reactions": {
                # Rates as published. No serious-adverse-event rate is given in
                # the label, so none is recorded; the discontinuation rate is
                # the closest published measure and is stored as itself.
                "value": [
                    {"reaction": "Injection site reaction", "drug_pct": 8.0, "placebo_pct": 2.0},
                    {"reaction": "Arthralgia", "drug_pct": 5.0, "placebo_pct": 4.0},
                    {"reaction": "Bronchitis", "drug_pct": 4.0, "placebo_pct": 3.0},
                ],
                "discontinuation_due_to_ae_pct": 2.5,
                "placebo_discontinuation_pct": 1.9,
                "serious_ae_rate_published": False,
                "source_name": "FDA prescribing information (LEQVIO), Adverse Reactions, via DailyMed",
                "source_url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=6fc0afca-4513-4c35-b594-6544aee29a44",
                "retrieved": "2026-08-03",
                "quote": ("adverse reactions led to discontinuation of treatment in 2.5% of patients "
                          "treated with LEQVIO and 1.9% of patients treated with placebo"),
            },
        },
        # Deliberately NOT verified yet — no authoritative Indian source read.
        # The workbook's price and brand list remain flagged as unverified.
        "not_yet_verified": [
            "india_price_per_dose",
            "india_brands",
            "india_approval_date",
        ],
    },
}


def _merged() -> Dict[str, Dict[str, Any]]:
    """Generated FDA-label facts, overlaid with hand-curated entries."""
    merged: Dict[str, Dict[str, Any]] = {}
    for key, rec in DAILYMED_FACTS.items():
        merged[key] = {**rec, "facts": dict(rec.get("facts", {}))}
    for key, rec in VERIFIED_FACTS.items():
        if key in merged:
            merged[key]["facts"].update(rec.get("facts", {}))
            merged[key]["not_yet_verified"] = rec.get("not_yet_verified", [])
        else:
            merged[key] = rec
    return merged


def get_verified(molecule_or_brand: str) -> Optional[Dict[str, Any]]:
    """Return the verified-fact record for a molecule, or None."""
    if not molecule_or_brand:
        return None
    return _merged().get(molecule_or_brand.strip().lower())


def verified_value(molecule: str, fact_key: str):
    """Return (value, provenance) for a verified fact, or (None, None)."""
    rec = get_verified(molecule)
    if not rec:
        return None, None
    fact = rec.get("facts", {}).get(fact_key)
    if not fact:
        return None, None
    provenance = {k: fact.get(k) for k in ("source_name", "source_url", "retrieved", "quote")
                  if fact.get(k) is not None}
    return fact.get("value"), provenance


def doses_per_year(molecule: str):
    """Loading-dose regimen as (year_1_doses, maintenance_doses), or (None, None)."""
    rec = get_verified(molecule)
    if not rec:
        return None, None
    sched = rec.get("facts", {}).get("dosing_schedule") or {}
    return sched.get("doses_year_1"), sched.get("doses_maintenance")


def verification_summary() -> Dict[str, Any]:
    """What has been source-verified so far, for surfacing in the UI."""
    all_recs = _merged()
    return {
        "molecules_verified": len(all_recs),
        "unmatched": DAILYMED_UNMATCHED,
        "molecules": {
            name: {
                "verified_fields": sorted(rec.get("facts", {}).keys()),
                "outstanding": rec.get("not_yet_verified", []),
                "sources": sorted({f.get("source_url") for f in rec.get("facts", {}).values()
                                   if f.get("source_url")}),
            }
            for name, rec in all_recs.items()
        },
    }
