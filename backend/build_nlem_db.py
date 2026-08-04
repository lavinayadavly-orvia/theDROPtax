"""
Load the National List of Essential Medicines (NLEM 2022).

NLEM membership is the gate for statutory price control: a molecule on the
list, in a listed formulation, falls under DPCO scheduling and has a ceiling
price. Absence from the list is equally informative — the manufacturer sets
the price freely.

The list also assigns a level of healthcare to each medicine:

    P  Primary      health centre / sub-centre
    S  Secondary    district hospital
    T  Tertiary     specialist / referral centre

That tells you where a drug is expected to be dispensed, which bears directly
on whether a patient meets it in an outpatient setting or only on referral.

Source
------
NLEM 2022, published by NPPA (nppa.gov.in/en/nlem2022). The PDF is bilingual;
the Hindi gazette text occupies the first ~60 pages and the English list
follows. Only the English list is parsed.

Rows read as:  <section> <Medicine> <levels> <dosage form and strength>

Nothing is inferred. A line that does not match is skipped and counted, not
guessed at.
"""
import os
import re
import ssl
import argparse
import asyncio
import urllib.request
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "droptax")

SOURCE_NAME = "National List of Essential Medicines 2022 (NLEM), via NPPA"
SOURCE_PAGE = "https://nppa.gov.in/en/nlem2022"
PDF_URL = ("https://nppa.gov.in/storage/uploads/pdf/"
           "nlem-2022pdf-0cd1d2b28855bf30128875ab19fc5304.pdf")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

# "21.5.2 Homatropine P,S,T Drops 2%"  /  "10.2.1 Atenolol S,T Tablet 50 mg"
NLEM_ROW = re.compile(
    r"^\s*(\d+(?:\.\d+)+)\s+"                     # section
    r"([A-Za-z][A-Za-z0-9\-+'’(),\.\* ]{2,60}?)\s*\**\s+"  # medicine (with footnote markers)
    r"((?:[PST])(?:\s*,\s*[PST])*)\b\s*"          # care levels
    r"(.*)$"                                       # formulation
)
LEVEL_NAMES = {"P": "Primary", "S": "Secondary", "T": "Tertiary"}


def download(path):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE          # nppa.gov.in serves an incomplete chain
    req = urllib.request.Request(PDF_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180, context=ctx) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return path


def parse(path):
    import pypdf
    reader = pypdf.PdfReader(path)
    entries, skipped = {}, 0
    for page in reader.pages:
        text = page.extract_text() or ""
        # Skip the Hindi gazette pages entirely
        if len(re.findall(r"[ऀ-ॿ]", text)) > len(re.findall(r"[A-Za-z]", text)):
            continue
        for line in text.split("\n"):
            line = re.sub(r"\s+", " ", line).strip()
            if not line or len(line) < 8:
                continue
            m = NLEM_ROW.match(line)
            if not m:
                if re.match(r"^\d+(?:\.\d+)+\s+[A-Za-z]", line):
                    skipped += 1
                continue
            section, medicine, levels, formulation = m.groups()
            medicine = medicine.strip(" ,.-*")
            if not medicine or medicine.lower() in ("medicine", "section"):
                continue
            lv = sorted({x.strip() for x in levels.split(",") if x.strip() in LEVEL_NAMES})
            key = medicine.lower()
            rec = entries.setdefault(key, {
                "medicine": medicine,
                "nlem_section": section,
                "care_levels": lv,
                "care_levels_expanded": [LEVEL_NAMES[x] for x in lv],
                "formulations": [],
            })
            if formulation and formulation not in rec["formulations"]:
                rec["formulations"].append(formulation.strip()[:120])
    return list(entries.values()), skipped


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    path = args.pdf or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".nlem_2022.pdf")
    if not os.path.exists(path):
        print("Downloading NLEM 2022…")
        download(path)

    print(f"Parsing {path}")
    entries, skipped = parse(path)
    print(f"  {len(entries)} medicines on the list")
    print(f"  {skipped} numbered line(s) skipped as unmatched (not guessed at)")

    if args.dry_run:
        for e in entries[:12]:
            print(f"    {e['nlem_section']:9} {e['medicine'][:28]:30} "
                  f"{'/'.join(e['care_levels']):8} {len(e['formulations'])} formulation(s)")
        return

    if not MONGO_URL:
        raise SystemExit("MONGO_URL is not set.")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    await db.nlem.delete_many({})
    for e in entries:
        e.update({"source_name": SOURCE_NAME, "source_url": SOURCE_PAGE,
                  "source_pdf": PDF_URL, "retrieved_utc": stamp})
    if entries:
        await db.nlem.insert_many(entries)

    # Flag our own catalogue. Absence is recorded explicitly, not left blank.
    listed = {e["medicine"].lower(): e for e in entries}
    on, off = 0, 0
    async for d in db.drugs.find({}, {"_id": 0, "name": 1}):
        name = d["name"]
        token = re.split(r"[^A-Za-z]+", name.lower())[0]
        match = listed.get(name.lower())
        if not match and len(token) > 4:
            match = next((v for k, v in listed.items() if k.startswith(token)), None)
        if match:
            on += 1
            # update_many, not update_one: a molecule can hold several catalogue
            # rows under one name — nifedipine appears under hypertension and
            # again under tocolysis. update_one flagged only the first and left
            # the second silently unlabelled.
            await db.drugs.update_many({"name": name}, {"$set": {
                "nlem_2022": {
                    "listed": True,
                    "section": match["nlem_section"],
                    "care_levels": match["care_levels_expanded"],
                    "matched_as": match["medicine"],
                    "source_url": SOURCE_PAGE,
                    "retrieved_utc": stamp,
                },
                "price_controlled": True,
            }})
        else:
            off += 1
            await db.drugs.update_many({"name": name}, {"$set": {
                "nlem_2022": {"listed": False, "source_url": SOURCE_PAGE, "retrieved_utc": stamp},
                "price_controlled": False,
            }})

    print(f"\n✅ loaded {len(entries)} NLEM medicines into '{DB_NAME}'.nlem")
    print(f"   catalogue flagged: {on} on the list (price-controlled), {off} not listed")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
