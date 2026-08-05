"""
MSO rate contract — what the government actually pays.

This is the third price a molecule has in India, and the lowest. Aceclofenac
100 mg is contracted at 53 paise a tablet here, sells at 72 paise over a TNMSC
counter, and carries a branded retail price several times either. The platform
has been modelling one price for a market that has at least three.

It also anchors a payer channel: CGHS medicine pricing follows the MSO bulk
procurement rate where a rate contract exists, and the NPPA ceiling where none
does. So this file plus the 1,012 NPPA ceilings we already hold covers both
legs of the CGHS price.

Every row carries its own contract window, which matters more than it looks —
a rate is only the rate between its start and end dates, and several run to
different ends. A price quoted outside its window is not a price.

Source
------
Medical Stores Organisation rate contract, supplied as PDF. Columns are
S.No, VMS Code, Drug Name, Drug Type, Rate/Unit, Packing Details, Contract
Start, Contract End, Batch Size. Read with pdfplumber's table extractor.

MSO's own site publishes these, but every menu item on mso-gmsd.in resolves to
/portal/undefined, so the file cannot currently be fetched from source and is
loaded from a supplied copy. That is a provenance weakness and is recorded on
every row.

Usage
-----
    python3 build_mso_rate_contract.py --pdf ~/Downloads/download.pdf --dry-run
    python3 build_mso_rate_contract.py --pdf ~/Downloads/download.pdf
"""
import os
import re
import argparse
import asyncio
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from core.scope import is_oncology

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "droptax")

SOURCE_NAME = "Medical Stores Organisation rate contract"
SOURCE_URL = "https://mso-gmsd.in/MSO_PORTAL/msowebsite/portal/home"

RATE = re.compile(r"([\d,]+\.?\d*)\s*/\s*(\w+)")
DATE = re.compile(r"(\d{1,2})\s*-\s*([A-Za-z]{3})\s*-\s*(\d{4})")
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
# "Strip of 10 Tablet", "3 ml Amp", "30 Gm Tube", "60 ml Bottle"
PACK_COUNT = re.compile(r"strip of\s*(\d+)|pack of\s*(\d+)|(\d+)\s*(?:'s|nos?)\b",
                        re.IGNORECASE)


def clean(c):
    if c is None:
        return None
    s = re.sub(r"\s+", " ", str(c)).strip()
    return s or None


def parse_date(text):
    if not text:
        return None
    m = DATE.search(text.replace("\n", " "))
    if not m:
        return None
    mon = MONTHS.get(m.group(2)[:3].lower())
    if not mon:
        return None
    try:
        return datetime(int(m.group(3)), mon, int(m.group(1))).date().isoformat()
    except ValueError:
        return None


def parse_rate(text):
    """Rate per unit, and what the unit is. No unit means no usable rate."""
    if not text:
        return None, None
    m = RATE.search(text.replace("\n", " "))
    if not m:
        return None, None
    try:
        return float(m.group(1).replace(",", "")), m.group(2)
    except ValueError:
        return None, None


def pack_size(text):
    """Units per pack, where the packing text states one."""
    if not text:
        return None
    m = PACK_COUNT.search(text)
    if not m:
        return None
    for g in m.groups():
        if g:
            return int(g)
    return None


def parse_pdf(path):
    import pdfplumber
    records, skipped = [], 0
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table:
                    cells = [clean(c) for c in row]
                    joined = " ".join(c for c in cells if c).lower()
                    if not joined or "drug name" in joined or "vms" in joined[:40]:
                        continue
                    cells = (cells + [None] * 9)[:9]
                    (serial, code, name, dtype, rate_raw,
                     packing, start, end, batch) = cells
                    if not name:
                        skipped += 1
                        continue
                    rate, unit = parse_rate(rate_raw)
                    if rate is None:
                        # A row with no readable rate is not a price. Kept so
                        # the count is honest, but flagged rather than dropped.
                        skipped += 1
                    per_pack = pack_size(packing)
                    records.append({
                        # VMS is the code's own label in the contract. Not
                        # expanded here because I have not read what it stands
                        # for, and a plausible guess is how "STC" became
                        # "Specialist Treatment Centre" instead of "Standing
                        # Technical Committee".
                        "vms_code": code,
                        "drug_name": name.replace("\n", " "),
                        "drug_type": dtype,
                        "rate_per_unit_inr": rate,
                        "rate_unit": unit,
                        "rate_raw": rate_raw,
                        "packing": packing,
                        "units_per_pack": per_pack,
                        "contract_start": parse_date(start),
                        "contract_end": parse_date(end),
                        "batch_size": int(batch) if (batch or "").isdigit() else None,
                        "source_name": SOURCE_NAME,
                        "source_url": SOURCE_URL,
                        "provenance_note": (
                            "Loaded from a supplied copy. mso-gmsd.in resolves every "
                            "menu item to /portal/undefined, so this could not be "
                            "fetched from source."),
                    })
    for r in records:
        excluded, why = is_oncology(r["drug_name"], None)
        r["out_of_scope"] = excluded
        r["out_of_scope_reason"] = why
    return records, skipped


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=os.path.expanduser("~/Downloads/download.pdf"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    records, skipped = parse_pdf(args.pdf)
    priced = [r for r in records if r["rate_per_unit_inr"] is not None]
    windows = {(r["contract_start"], r["contract_end"]) for r in records
               if r["contract_start"]}
    print(f"  {len(records)} rows · {len(priced)} with a readable rate · "
          f"{skipped} without")
    print(f"  {len(windows)} distinct contract window(s)")
    print(f"  {sum(1 for r in records if r['out_of_scope'])} marked out of scope")

    if priced:
        cheap = sorted(priced, key=lambda r: r["rate_per_unit_inr"])[:6]
        dear = sorted(priced, key=lambda r: -r["rate_per_unit_inr"])[:4]
        print("\n  cheapest contracted rates:")
        for r in cheap:
            print(f"    Rs{r['rate_per_unit_inr']:>10.4f}/{str(r['rate_unit']):4} "
                  f"{r['drug_name'][:46]}")
        print("\n  dearest:")
        for r in dear:
            print(f"    Rs{r['rate_per_unit_inr']:>10.4f}/{str(r['rate_unit']):4} "
                  f"{r['drug_name'][:46]}")

    if args.dry_run:
        print("\n  (dry run — nothing written)")
        return

    if not MONGO_URL:
        raise SystemExit("MONGO_URL is not set.")
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for r in records:
        r["retrieved_utc"] = stamp
    await db.mso_rate_contract.delete_many({})
    if records:
        await db.mso_rate_contract.insert_many(records)
    print(f"\n✅ loaded {len(records)} into '{DB_NAME}'.mso_rate_contract")


if __name__ == "__main__":
    asyncio.run(main())
