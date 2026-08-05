"""
CGHS restricted medicines — the access gate for the government-employee channel.

CGHS covers central government employees and pensioners, and it is a distinct
channel from retail and from PM-JAY. Two things govern a drug there, and they
are separate questions:

    WHO APPROVES IT    the restricted lists, loaded here
    WHAT IT COSTS      MSO rate contract if one exists, else the NPPA ceiling

A "restricted" medicine is not excluded — it needs authorisation, and the two
lists differ in who gives it.

STC is the **Standing Technical Committee**: a board of medical experts that
must review and clear the patient's file. A local wellness centre cannot
approve these. The route is triggered by COST — a restricted drug above about
Rs10,000 per unit of administration, above Rs50,000 a month, or a cancer cycle
above Rs15,00,000.

NON-STC drugs are already standardised in the CGHS digital workflow, so the
local Additional Director or the Chief Medical Officer of the Medical Store
Depot approves and dispatches directly through the portal, with no committee.

The lists are not static. An STC drug approved in more than 20 separate patient
cases within six months transitions automatically to the Non-STC online list.
Immunotherapy is the standing exception and stays under STC regardless.

Inclisiran (Sybrava) and evolocumab are both on the STC list, so a CGHS patient
reaches them only after committee clearance — an access fact with a lead time
attached, which a commercial team needs and no clinical argument changes.

Pricing is not in these files
-----------------------------
The lists carry the medicine and its dosage form, nothing else. Price is
resolved separately: CGHS anchors to Medical Stores Organisation bulk
procurement rates where a rate contract exists, and falls back to the NPPA
ceiling price otherwise. We already hold 1,012 NPPA ceilings, so the fallback
leg is computable today; the MSO leg is not, because MSO publishes rate
contracts as PDFs behind a navigation that resolves every menu item to
/portal/undefined.

So a CGHS price derived here would be the fallback, and must say so rather than
present itself as the CGHS price.

Source
------
CGHS restricted medicine lists, supplied as CSV:
    STC_Restricted_Medicine.csv       specialist-initiated
    NON_STC_Restricted_Medicine.csv   restricted, not specialist-gated

Usage
-----
    python3 build_cghs_restrictions.py --dry-run
    python3 build_cghs_restrictions.py --dir ~/Downloads
"""
import os
import re
import csv
import argparse
import asyncio
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from core.scope import is_oncology

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "droptax")

SOURCE_NAME = "CGHS restricted medicine lists"
FILES = [("STC_Restricted_Medicine.csv", "STC", True),
         ("NON_STC_Restricted_Medicine.csv", "NON_STC", False)]

# Cost thresholds that route a restricted medicine to the Standing Technical
# Committee rather than to local approval. These are the published triggers.
STC_TRIGGERS = {
    "per_administration_inr": 10000,
    "per_month_inr": 50000,
    "cancer_cycle_inr": 1500000,
    "non_stc_cancer_cycle_below_inr": 100000,
    "auto_transition_cases_in_6_months": 20,
    "always_stc": "immunotherapy",
}

# "INJ. INCLISIRAN (SYBRAVA) 284 MG/1.5 ML (PACK SIZE 1X1)"
PACK = re.compile(r"\(\s*PACK\s*(?:SIZE)?\s*[^)]*\)", re.IGNORECASE)
BRAND = re.compile(r"\(([A-Z][A-Za-z][A-Za-z\- ]{2,28})\)")
FORM_PREFIX = re.compile(r"^\s*(INJ\.?|TAB\.?|CAP\.?|SYP\.?)\s+", re.IGNORECASE)
STRENGTH = re.compile(r"\b\d+(?:\.\d+)?\s*(?:MG|MCG|G|ML|IU|%)(?:\s*/\s*[\d.]*\s*ML)?\b",
                      re.IGNORECASE)


def parse_entry(raw_name, dosage_type):
    """Pull molecule, brand and strength out of one list entry.

    The entry is a dispensing description, not a molecule name, so what comes
    out is a best reading and is stored alongside the original. Nothing is
    dropped: the raw string is always kept.
    """
    name = PACK.sub(" ", raw_name or "")
    brand = None
    m = BRAND.search(name)
    if m:
        candidate = m.group(1).strip()
        # A parenthetical that is a dose form or route is not a brand.
        if not re.fullmatch(r"(?i)(inj|tab|cap|caps|vial|pfs|pfp|solution|liquid|"
                            r"device|syringe|patch|oral|iv|sc|im)\.?", candidate):
            brand = candidate
            name = name.replace(m.group(0), " ")
    strengths = STRENGTH.findall(name)
    molecule = FORM_PREFIX.sub("", STRENGTH.sub(" ", name))
    molecule = re.sub(r"\b(INJ|TAB|CAP|CAPS|VIAL|PFS|PFP|SOLUTION|LIQUID|DEVICE|"
                      r"SYRINGE|PATCH|MULTIDOSE|PREFILLED|PEN)\b", " ",
                      molecule, flags=re.IGNORECASE)
    molecule = re.sub(r"[^A-Za-z0-9\-+/ ]+", " ", molecule)
    molecule = re.sub(r"\s+", " ", molecule).strip(" -+/")
    return {
        "molecule_read": molecule.title() or None,
        "brand_read": brand,
        "strength_read": strengths[0] if strengths else None,
        "dosage_type": dosage_type,
        "raw": raw_name,
    }


def load(path, list_name, specialist_only):
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            raw = (row.get("Name of Restricted Medicine") or "").strip()
            if not raw:
                continue
            rec = parse_entry(raw, (row.get("Dosage type") or "").strip() or None)
            rec.update({
                "cghs_list": list_name,
                "standing_technical_committee_required": specialist_only,
                "approved_by": ("Standing Technical Committee" if specialist_only
                                else "Additional Director / CMO of the Medical Store Depot"),
                "restricted": True,
                "stc_cost_triggers": STC_TRIGGERS if specialist_only else None,
                "source_name": SOURCE_NAME,
                "source_file": os.path.basename(path),
            })
            excluded, why = is_oncology(rec["molecule_read"], None)
            rec["out_of_scope"] = excluded
            rec["out_of_scope_reason"] = why
            out.append(rec)
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.expanduser("~/Downloads"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    records = []
    for filename, list_name, specialist in FILES:
        path = os.path.join(args.dir, filename)
        if not os.path.exists(path):
            print(f"  ! missing: {path}")
            continue
        rows = load(path, list_name, specialist)
        in_scope = sum(1 for r in rows if not r["out_of_scope"])
        print(f"  {filename:34} {len(rows):>4} entries · {in_scope:>4} in scope"
              f"{' · Standing Technical Committee' if specialist else ''}")
        records.extend(rows)

    print(f"\n  {len(records)} restricted medicines")
    print(f"  {sum(1 for r in records if r['standing_technical_committee_required'])} "
          f"need Standing Technical Committee clearance")
    print(f"  {sum(1 for r in records if r['out_of_scope'])} marked out of scope (oncology)")
    named = sum(1 for r in records if r["brand_read"])
    print(f"  {named} name a brand in the entry")

    if args.dry_run:
        print("\n  in-scope sample:")
        for r in [x for x in records if not x["out_of_scope"]][:10]:
            gate = "STC" if r["standing_technical_committee_required"] else "local"
            print(f"    {gate:11} {str(r['molecule_read'])[:34]:36} "
                  f"{str(r['brand_read'] or ''):12} {r['strength_read'] or ''}")
        print("\n  (dry run — nothing written)")
        return

    if not MONGO_URL:
        raise SystemExit("MONGO_URL is not set.")
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for r in records:
        r["retrieved_utc"] = stamp
    await db.cghs_restricted.delete_many({})
    if records:
        await db.cghs_restricted.insert_many(records)
    print(f"\n✅ loaded {len(records)} into '{DB_NAME}'.cghs_restricted")


if __name__ == "__main__":
    asyncio.run(main())
