"""
Jan Aushadhi product and MRP list — the fourth price, and the true floor.

PMBJP sells unbranded generics through its own Kendras at prices set centrally.
For a molecule that appears here, this is the least a patient can pay in India
anywhere, which makes it the reference point every other price should be read
against: aceclofenac 100 mg is Rs8.25 for ten here, Rs0.53 a tablet on the MSO
contract, Rs0.72 over a TNMSC counter, and several times either as a brand.

How this stopped being blocked
------------------------------
It was logged as "SPA serving an app shell for every path including its own
API" after two attempts. Every part of that was wrong except the symptom.

The site is a React app whose bundle names its own endpoints, and the base URL
is in there too:

    baseURL: "https://janaushadhi.gov.in:8443/"

Port 8443, not 443. Every request I had made went to the normal port and got
the app shell, which looked exactly like an SPA refusing to serve data.

The endpoint itself, /api/v1/website/getAllProductForWeb, then returned 500 to
every payload guessed at it. Hooking window.fetch in the browser and clicking
the site's own menu item gave the real body — `pageIndex`, not `pageNo`, plus a
required `columnName` — and the page's own "Download Files" button builds the
whole list client-side as a blob, which is where this CSV came from.

Direct calls from outside the browser still 500 even with the exact body, so
the file is supplied rather than fetched, and every row says so.

Source
------
janaushadhi.gov.in -> Product Portfolio -> Product & MRP List.
Columns: Sr No, Drug Code, Generic Name, Unit Size, MRP, Group Name.

Zero-MRP rows are real and are kept: the site notes "Zero MRP products are
under process", so a zero means not yet priced, not free.

Usage
-----
    python3 build_janaushadhi.py --dry-run
    python3 build_janaushadhi.py --csv ~/Downloads/janaushadhi_product_mrp.csv
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

SOURCE_NAME = "Jan Aushadhi (PMBJP) product and MRP list"
SOURCE_URL = "https://janaushadhi.gov.in/product-portfolio/product-mrp-list"
DEFAULT_CSV = os.path.expanduser("~/Downloads/janaushadhi_product_mrp.csv")

# "10's", "14's", "100 Ear Buds", "15 g", "One in Mono-Carton"
PACK_COUNT = re.compile(r"^\s*(\d+)\s*'?s\b|^\s*(\d+)\s+", re.IGNORECASE)
STRENGTH = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|%)\b", re.IGNORECASE)


def pack_units(unit_size):
    """Units in the pack, where the text states a count."""
    if not unit_size:
        return None
    m = PACK_COUNT.match(unit_size)
    if not m:
        return None
    for g in m.groups():
        if g:
            try:
                return int(g)
            except ValueError:
                return None
    return None


def molecule_of(generic_name):
    """Leading molecule token, for matching against the catalogue."""
    if not generic_name:
        return None
    head = STRENGTH.split(generic_name)[0]
    head = re.sub(r"\b(tablets?|capsules?|injections?|ip|bp|usp|gel|cream|"
                  r"ointment|syrup|suspension|solution|drops?|powder)\b", " ",
                  head, flags=re.IGNORECASE)
    head = re.sub(r"[^A-Za-z ]+", " ", head)
    head = re.sub(r"\s+", " ", head).strip()
    return head or None


def load(path):
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = (row.get("Generic Name") or "").strip()
            if not name:
                continue
            raw_mrp = (row.get("MRP") or "").strip()
            try:
                mrp = float(raw_mrp)
            except ValueError:
                mrp = None
            units = pack_units(row.get("Unit Size"))
            rec = {
                "drug_code": (row.get("Drug Code") or "").strip() or None,
                "generic_name": name,
                "molecule": molecule_of(name),
                "unit_size": (row.get("Unit Size") or "").strip() or None,
                "units_per_pack": units,
                "mrp_inr": mrp,
                # Zero is "under process" per the site's own note, not free.
                "priced": bool(mrp),
                "mrp_per_unit_inr": (round(mrp / units, 4)
                                     if (mrp and units) else None),
                "group_name": (row.get("Group Name") or "").strip() or None,
                "source_name": SOURCE_NAME,
                "source_url": SOURCE_URL,
                "provenance_note": (
                    "Exported from the site's own Download Files button. Direct "
                    "API calls to port 8443 return 500 from outside the browser."),
            }
            excluded, why = is_oncology(rec["molecule"], rec["group_name"])
            rec["out_of_scope"] = excluded
            rec["out_of_scope_reason"] = why
            out.append(rec)
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        raise SystemExit(f"Not found: {args.csv}")
    records = load(args.csv)
    priced = [r for r in records if r["priced"]]
    per_unit = [r for r in records if r["mrp_per_unit_inr"] is not None]
    groups = {r["group_name"] for r in records if r["group_name"]}

    print(f"  {len(records)} products · {len(priced)} priced · "
          f"{len(records) - len(priced)} at zero (under process, not free)")
    print(f"  {len(per_unit)} with a per-unit price · {len(groups)} therapeutic groups")
    print(f"  {sum(1 for r in records if r['out_of_scope'])} marked out of scope")

    if args.dry_run:
        cheap = sorted(per_unit, key=lambda r: r["mrp_per_unit_inr"])[:5]
        print("\n  cheapest per unit:")
        for r in cheap:
            print(f"    Rs{r['mrp_per_unit_inr']:>8.4f}  {r['generic_name'][:58]}")
        print("\n  (dry run — nothing written)")
        return

    if not MONGO_URL:
        raise SystemExit("MONGO_URL is not set.")
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for r in records:
        r["retrieved_utc"] = stamp
    await db.janaushadhi.delete_many({})
    if records:
        await db.janaushadhi.insert_many(records)
    print(f"\n✅ loaded {len(records)} into '{DB_NAME}'.janaushadhi")


if __name__ == "__main__":
    asyncio.run(main())
