"""
CDSCO biologicals register — who is permitted to make or import what, in India.

The "List of Approved New Drugs" covers small molecules and misses the drugs
this platform exists for. Inclisiran was cleared in July 2023 by a Subject
Expert Committee under an import permission, and tenecteplase does not appear
there at all — yet Hetero Biopharma was permitted to manufacture and market it
on 31 January 2023.

That permission lives in a different stream, and it is the one that answers the
Indian question:

    CT-21   approved for MANUFACTURE and marketing  -> who makes it here
    CT-18   approved for IMPORT and marketing       -> how an innovator enters

Both name the firm, so this is the source for the competition signal that
replaces "exclusivity". A molecule with eight CT-21 permissions to eight
companies is contested here whatever its patent status is anywhere else.

Scope: r-DNA origin only, so recombinant proteins and biosimilars. Small
molecules stay in the new-drugs register. Neither is complete on its own, and
absence from both is still not evidence a drug is unapproved in India.

Source
------
cdsco.gov.in -> Biologicals -> rDNA. Two consolidated PDFs cover Jan 2020 to
June 2026, plus one for permissions up to 2019. They are real tables, so they
are read with pdfplumber's table extractor rather than by pattern-matching
flowed text — which is what the new-drugs lists needed and what made that
parser fragile.

Usage
-----
    python3 build_cdsco_biologics.py --dry-run
    python3 build_cdsco_biologics.py
"""
import os
import re
import ssl
import socket
import argparse
import asyncio
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "droptax")

BASE = ("https://cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2018/"
        "UploadBiologicalrDNA/")
SOURCE_PAGE = "https://cdsco.gov.in/opencms/opencms/en/biologicals/rDNA/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

SOURCES = [
    ("CT-21 Approvals Jan 2020 - June 2026.pdf", "manufacture"),
    ("CT-18 Approvals Jan, 2020 - June 2026.pdf", "import"),
    ("Import and market permission till 2019.pdf", "import"),
]

DATE = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b")
HEADER_HINTS = ("s. no", "s.no", "name of the firm", "list of new drugs",
                "annexure", "date of permission")
NOT_APPLICABLE = re.compile(r"^\s*not\s+applicable\s*\.?\s*$", re.IGNORECASE)


def _ctx():
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE          # cdsco.gov.in serves an incomplete chain
    return c


def download(filename, cache_dir):
    path = os.path.join(cache_dir, re.sub(r"[^A-Za-z0-9._-]+", "_", filename))
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    url = BASE + urllib.parse.quote(filename)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=240, context=_ctx()) as r:
        data = r.read()
    if data[:4] != b"%PDF":
        raise ValueError(f"not a PDF ({len(data)} bytes)")
    with open(path, "wb") as f:
        f.write(data)
    return path


def clean(cell):
    if cell is None:
        return None
    s = re.sub(r"\s+", " ", str(cell)).strip()
    return s or None


def parse_date(text):
    if not text:
        return None
    m = DATE.search(text)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000
    try:
        if not (2000 <= y <= datetime.now().year + 1):
            return None
        return datetime(y, mo, d).date().isoformat()
    except ValueError:
        return None


def parse_pdf(path, permission_type, source_name):
    """Rows out of one consolidated table.

    A cell can wrap onto a following row with an empty serial number. Those
    continue the record above rather than starting a new one — treating them as
    new rows is what produced fragment 'approvals' in the small-molecule parser.
    """
    import pdfplumber

    records, skipped = [], 0
    current = None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table:
                    cells = [clean(c) for c in row]
                    joined = " ".join(c for c in cells if c).lower()
                    if not joined:
                        continue
                    if any(h in joined for h in HEADER_HINTS):
                        continue
                    # Pad or trim to the seven documented columns.
                    cells = (cells + [None] * 7)[:7]
                    serial, firm, date, permission, drug, indication, dosage = cells

                    if serial and serial.strip().rstrip(".").isdigit():
                        if current:
                            records.append(current)
                        current = {
                            "serial": int(serial.strip().rstrip(".")),
                            "firm": firm,
                            "permission_date": parse_date(date),
                            "permission_date_raw": date,
                            "permission_no": permission,
                            "drug_name": drug,
                            "indication": None if (indication and NOT_APPLICABLE.match(indication))
                                          else indication,
                            "dosage_form": dosage,
                            "permission_type": permission_type,
                            "source_name": source_name,
                            "source_url": SOURCE_PAGE,
                        }
                    elif current:
                        # Continuation: append each cell to the field it belongs to.
                        for key, value in (("firm", firm), ("drug_name", drug),
                                           ("indication", indication),
                                           ("dosage_form", dosage)):
                            if value:
                                current[key] = f"{current[key]} {value}".strip() \
                                    if current.get(key) else value
                        if date and not current.get("permission_date"):
                            current["permission_date"] = parse_date(date)
                    else:
                        skipped += 1
    if current:
        records.append(current)

    # A row with no firm and no drug carries nothing usable.
    usable = [r for r in records if r.get("drug_name") or r.get("firm")]
    skipped += len(records) - len(usable)
    return usable, skipped


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    socket.setdefaulttimeout(240)

    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cdsco")
    os.makedirs(cache, exist_ok=True)

    all_records, total_skipped = [], 0
    for filename, permission_type in SOURCES:
        try:
            path = download(filename, cache)
        except Exception as e:
            print(f"  ! {filename[:50]}: {e}")
            continue
        try:
            recs, skipped = parse_pdf(path, permission_type,
                                      f"CDSCO r-DNA register — {filename}")
        except Exception as e:
            print(f"  ! parse failed for {filename[:44]}: {e}")
            continue
        firms = {r["firm"] for r in recs if r.get("firm")}
        dated = sum(1 for r in recs if r.get("permission_date"))
        print(f"  {filename[:46]:48} {len(recs):>4} rows · {dated:>4} dated · "
              f"{len(firms):>3} firms")
        all_records.extend(recs)
        total_skipped += skipped

    firms = {r["firm"] for r in all_records if r.get("firm")}
    print(f"\n  {len(all_records)} permissions · {len(firms)} distinct firms")
    print(f"  {sum(1 for r in all_records if r['permission_type'] == 'manufacture')} "
          f"manufacture, "
          f"{sum(1 for r in all_records if r['permission_type'] == 'import')} import")
    print(f"  {total_skipped} unusable row(s) dropped (no firm and no drug)")

    if args.dry_run:
        print("\n  sample:")
        for r in all_records[:8]:
            print(f"    {str(r['permission_date']):12} {str(r['firm'])[:30]:32} "
                  f"{str(r['drug_name'])[:34]}")
        print("\n  (dry run — nothing written)")
        return

    if not MONGO_URL:
        raise SystemExit("MONGO_URL is not set.")
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for r in all_records:
        r["retrieved_utc"] = stamp
    await db.cdsco_biologics.delete_many({})
    if all_records:
        await db.cdsco_biologics.insert_many(all_records)
    print(f"\n✅ loaded {len(all_records)} permissions into '{DB_NAME}'.cdsco_biologics")


if __name__ == "__main__":
    asyncio.run(main())
