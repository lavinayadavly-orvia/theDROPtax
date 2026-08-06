"""
Export the curated datasets as portable artefacts.

These were assembled and cleaned for the DROP Tax platform, but the work is
reusable: the therapy-area registry, the structured indications, and the Indian
regulatory and price registers stand on their own.

Every artefact ships with its caveats in the manifest, and the same caveats are
repeated inside each file. That is the point. The prices rest on an assumed
once-daily dose, the brand counts are floors, and absence from a register is
not evidence a drug is unapproved — carried across to another project without
those, each of them becomes a confident false statement, which is exactly how
they entered this codebase in the first place.

Output
------
    artefacts/
        MANIFEST.md                     what each file is, and how far to trust it
        therapy_area_registry.json      37 indications, endpoints, normalisation
        drug_catalogue.json/.csv        218 molecules with every derived field
        indications.csv                 438 structured (drug x indication) rows
        nppa_ceiling_prices.csv         1,012 gazette-cited ceiling prices
        nlem_2022.csv                   239 essential medicines, care levels
        cdsco_new_drug_approvals.csv    India approvals with indication and date
        cdsco_biologics_permissions.csv who may make or import, by firm
        cghs_restricted_medicines.csv   who must approve a restricted medicine
        mso_rate_contract.csv           what central government pays
        janaushadhi_product_mrp.csv     PMBJP prices, the floor a patient pays
        verified_label_facts.json       DailyMed facts with verbatim quotes

Usage
-----
    python3 export_artefacts.py                  # writes ./artefacts
    python3 export_artefacts.py --out <dir>
"""
import os
import csv
import json
import argparse
import asyncio
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "droptax")

# Caveats travel with the data. Each is a fact about how far the file can be
# trusted, not a disclaimer.
CAVEATS = {
    "drug_catalogue.csv": [
        "213 of 218 prices are ESTIMATES. 156 are a per-unit retail price scaled "
        "to a month on an ASSUMED once-daily dose — a drug taken three times a "
        "day costs three times the figure shown. price_is_estimated and "
        "price_note carry this per row; do not use the number without them.",
        "Clinical endpoints are present for 1 molecule of 218.",
        "key_brands is a curated list of brands worth knowing, not every brand "
        "on the market. Counts derived from it are FLOORS.",
    ],
    "indications.csv": [
        "Split from free text on ';' only — commas never separate, because "
        "several rows carry commas inside parentheses.",
        "107 of 438 do not resolve to the therapy-area registry. They are kept "
        "and marked unmapped rather than forced to the nearest entry.",
    ],
    "nppa_ceiling_prices.csv": [
        "Statutory ceilings under DPCO 2013, each with its gazette notification "
        "number and date. A retailer may sell below the ceiling, never above.",
    ],
    "nlem_2022.csv": [
        "NLEM membership gates statutory price control. Absence from the list is "
        "equally informative — the manufacturer prices freely.",
    ],
    "cdsco_new_drug_approvals.csv": [
        "Covers small molecules. Thin before roughly 2009, and nine of the forty "
        "source lists are image tables with no text layer that could not be read.",
        "ABSENCE IS NOT NON-APPROVAL. Inclisiran, sacubitril and tenecteplase are "
        "all marketed in India and none appear here — they entered by import "
        "permission or Subject Expert Committee clearance, which is a different "
        "register.",
    ],
    "cdsco_biologics_permissions.csv": [
        "r-DNA origin only: recombinant proteins and biosimilars. CT-21 is "
        "permission to manufacture and market, CT-18 to import and market.",
        "out_of_scope marks oncology rows — the register is roughly a quarter "
        "oncology by volume and this platform covers CardioMetabolic and "
        "Women's Health. Rows are marked, not deleted.",
        "Better evidence than a curated brand list, but NOT more complete: the "
        "consolidated file lists one manufacturer for tenecteplase where a "
        "monthly file from the same register names another.",
    ],
    "verified_label_facts.json": [
        "ONE MOLECULE, NOT FIFTY. verify_from_dailymed.py checked 50 innovators; "
        "only inclisiran was ever persisted. Every field it does hold carries "
        "source_name, source_url, retrieved date and a verbatim quote.",
    ],
    "cghs_restricted_medicines.csv": [
        "Restricted does NOT mean excluded — it means the medicine needs "
        "authorisation. STC is the Standing Technical Committee, a board that "
        "must clear the patient's file; non-STC is approved locally by the "
        "Additional Director or CMO of the Medical Store Depot.",
        "The route is chosen by COST: above roughly Rs10,000 per administration, "
        "Rs50,000 a month, or a cancer cycle above Rs15,00,000.",
        "The lists move. An STC drug approved in more than 20 separate cases "
        "within six months transitions to the non-STC online list; immunotherapy "
        "is the standing exception.",
    ],
    "mso_rate_contract.csv": [
        "What central government actually pays. Every row carries its own "
        "contract window — a rate is only the rate between its dates.",
        "Loaded from a supplied copy: mso-gmsd.in resolves every menu item to "
        "/portal/undefined, so it could not be fetched from source.",
        "VMS is the code's own label in the contract and is deliberately NOT "
        "expanded, because it has not been read anywhere.",
    ],
    "janaushadhi_product_mrp.csv": [
        "PMBJP prices — for a molecule listed here this is close to the least a "
        "patient can pay in India, and the reference every other price should be "
        "read against.",
        "Zero MRP means UNDER PROCESS, not free. The site says so itself.",
    ],
    "therapy_area_registry.json": [
        "Per-indication endpoints with benefit direction and a normalisation "
        "spec. direction matters: LDL-C, HbA1c, blood pressure and menstrual "
        "blood loss are lower-better; functional independence and BMD are "
        "higher-better.",
    ],
}


def write_csv(path, rows, exclude=("_id",)):
    if not rows:
        return 0
    keys = []
    for r in rows:
        for k in r:
            if k not in keys and k not in exclude:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, ensure_ascii=False)
                            if isinstance(v, (dict, list)) else v)
                        for k, v in r.items() if k in keys})
    return len(rows)


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=str)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    root = args.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artefacts")
    os.makedirs(root, exist_ok=True)

    if not MONGO_URL:
        raise SystemExit("MONGO_URL is not set.")
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    written = {}

    # Therapy-area registry — the piece with no external source, so the most
    # reusable and the one worth carrying whole.
    from core.therapy_areas import INDICATION_REGISTRY
    write_json(os.path.join(root, "therapy_area_registry.json"),
               {"generated_utc": stamp,
                "caveats": CAVEATS["therapy_area_registry.json"],
                "indication_count": len(INDICATION_REGISTRY),
                "indications": INDICATION_REGISTRY})
    written["therapy_area_registry.json"] = len(INDICATION_REGISTRY)

    from core.verified_facts import VERIFIED_FACTS
    write_json(os.path.join(root, "verified_label_facts.json"),
               {"generated_utc": stamp,
                "caveats": CAVEATS["verified_label_facts.json"],
                "molecules": VERIFIED_FACTS})
    written["verified_label_facts.json"] = len(VERIFIED_FACTS)

    drugs = [d async for d in db.drugs.find({}, {"_id": 0})]
    write_json(os.path.join(root, "drug_catalogue.json"),
               {"generated_utc": stamp, "caveats": CAVEATS["drug_catalogue.csv"],
                "count": len(drugs), "drugs": drugs})
    written["drug_catalogue.csv"] = write_csv(
        os.path.join(root, "drug_catalogue.csv"), drugs)

    # One row per (drug x indication) — the unit the platform reasons about.
    rows = []
    for d in drugs:
        for i in d.get("indications") or []:
            rows.append({
                "drug": d.get("name"), "category": d.get("category"),
                "indication": i.get("text"),
                "registry_indication": i.get("registry_indication"),
                "indication_category": i.get("category"),
                "mapped": i.get("mapped"), "off_label": i.get("off_label"),
                "qualifier": i.get("qualifier"),
                "is_primary": i.get("text") == d.get("primary_indication"),
            })
    written["indications.csv"] = write_csv(os.path.join(root, "indications.csv"), rows)

    for coll, filename in (("ceiling_prices", "nppa_ceiling_prices.csv"),
                           ("nlem", "nlem_2022.csv"),
                           ("cdsco_approvals", "cdsco_new_drug_approvals.csv"),
                           ("cdsco_biologics", "cdsco_biologics_permissions.csv"),
                           ("cghs_restricted", "cghs_restricted_medicines.csv"),
                           ("mso_rate_contract", "mso_rate_contract.csv"),
                           ("janaushadhi", "janaushadhi_product_mrp.csv"),
                           ("support_programs", "support_programmes.csv")):
        docs = [x async for x in db[coll].find({}, {"_id": 0})]
        written[filename] = write_csv(os.path.join(root, filename), docs)

    lines = [
        "# DROP Tax — data artefacts",
        "",
        f"Exported {stamp} from the `{DB_NAME}` database.",
        "",
        "Curated for the DROP Tax platform and reusable on their own. Every file "
        "carries its caveats below, and they are repeated inside the JSON files. "
        "Carried across without them, each of these becomes a confident false "
        "statement — which is how several of them entered this codebase.",
        "",
        "**Scope: CardioMetabolic and Women's Health. No oncology.**",
        "",
        "**A molecule has at least four prices in India** — Jan Aushadhi, the MSO "
        "contract, a public counter, and branded retail, with MRP a ceiling above "
        "all of them. Any single figure needs to say which one it is.",
        "",
        "| File | Rows | What it is |",
        "|---|---|---|",
        "| `therapy_area_registry.json` | 37 | Indications with endpoints, benefit direction and normalisation |",
        "| `drug_catalogue.json` / `.csv` | 218 | Molecules with every derived field |",
        "| `indications.csv` | 438 | One row per (drug × indication) |",
        "| `nppa_ceiling_prices.csv` | 1,012 | Statutory ceilings, gazette-cited |",
        "| `nlem_2022.csv` | 239 | Essential medicines with care levels |",
        "| `cdsco_new_drug_approvals.csv` | 472 | India approvals, indication and date |",
        "| `cdsco_biologics_permissions.csv` | 486 | Who may make or import, by firm |",
        "| `cghs_restricted_medicines.csv` | 407 | Who must approve a restricted medicine, and on what cost trigger |",
        "| `mso_rate_contract.csv` | 525 | What central government pays, with contract windows |",
        "| `janaushadhi_product_mrp.csv` | 2,439 | PMBJP prices — the floor a patient can pay |",
        "| `verified_label_facts.json` | **1** | DailyMed facts with verbatim quotes. Inclisiran only |",
        "",
        "## How far to trust each file",
        "",
    ]
    for filename, notes in CAVEATS.items():
        lines.append(f"### `{filename}`")
        for n in notes:
            lines.append(f"- {n}")
        lines.append("")
    lines += [
        "## Two rules that apply to all of it",
        "",
        "1. **Absence is not a negative finding.** A molecule missing from a "
        "register is not evidence it is unapproved, unpriced or uncontested — "
        "the registers are incomplete in documented ways.",
        "2. **An estimate is not a measurement.** Where a field is flagged "
        "estimated, the assumption behind it is named in the same row. Strip "
        "the flag and you have manufactured a fact.",
        "",
    ]
    with open(os.path.join(root, "MANIFEST.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"artefacts -> {root}\n")
    for name, n in sorted(written.items()):
        print(f"  {name:38} {n:>6} rows")
    print(f"  {'MANIFEST.md':38} {'':>6}")


if __name__ == "__main__":
    asyncio.run(main())
