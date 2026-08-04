"""
Build the regulated-price database from NPPA.

NPPA ceiling prices are the statutory maximum for scheduled formulations under
DPCO 2013. They outrank any retail listing: a retailer may sell below the
ceiling, never above it. Each row here carries the gazette notification number
and date it was fixed, so a figure can be traced to the instrument that set it.

Source
------
Compendium of Prices, NPPA (nppa.gov.in) — a text PDF laid out as:

    NLEM section | Medicine | Dosage form & strength | Unit/Pack | Ceiling
    price (Rs.) | S.O. No. | Date of notification

Rows for additional formulations of the same molecule omit the section number
and molecule name, so the current molecule is carried forward.

Nothing is inferred. A row that does not parse cleanly is recorded as
unparsed rather than guessed at, and reported at the end.

Usage
-----
    python3 build_ceiling_price_db.py                 # download + parse + load
    python3 build_ceiling_price_db.py --pdf <path>    # parse a local copy
    python3 build_ceiling_price_db.py --dry-run       # parse, print, do not load
"""
import os
import re
import ssl
import json
import argparse
import asyncio
import urllib.request
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "droptax")

SOURCE_NAME = "NPPA Compendium of Prices 2022 (ceiling prices under DPCO 2013)"
SOURCE_PAGE = "https://nppa.gov.in/en/compendiumofprice"
PDF_URL = ("https://nppa.gov.in/storage/uploads/pdf/"
           "Compendium-Prices-2022pdf-464b22085495ff4e3f8700c0e00cf45d.pdf")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

# A priced row ends with: <price> <S.O. number> <dd.mm.yyyy>
ROW_TAIL = re.compile(r"([\d,]+\.\d{2})\s+([\dA-Za-z()\-/ ]+?)\s+(\d{2}\.\d{2}\.\d{4})\s*$")
# A row that starts a new molecule begins with an NLEM section number
MOLECULE_HEAD = re.compile(r"^(\d+(?:\.\d+)+)\s+([A-Za-z][A-Za-z0-9\-+'()/ ,\.]+?)\s{2,}|^(\d+(?:\.\d+)+)\s+([A-Z][a-z][A-Za-z0-9\-+'()/ ,\.]*)")
DOSAGE_WORDS = ("tablet", "capsule", "injection", "oral liquid", "drops", "syrup",
                "suspension", "cream", "ointment", "gel", "inhaler", "solution",
                "powder", "sachet", "patch", "spray", "infusion", "granules",
                "inhalation", "topical", "eye ", "ear ", "nasal", "rectal",
                "vaginal", "pessary", "lotion", "emulsion", "elixir", "dispersible",
                "prefilled", "implant", "device", "kit", "pump", "respirator")


def download(path):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE          # nppa.gov.in serves an incomplete chain
    req = urllib.request.Request(PDF_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return path


def join_wrapped(lines):
    """Rejoin rows split mid-cell (e.g. "Each Pack (10" / "ml) 19.95 ...")."""
    out = []
    for line in lines:
        line = line.rstrip()
        if not line.strip():
            continue
        if out and not ROW_TAIL.search(line) and not ROW_TAIL.search(out[-1]):
            out[-1] = out[-1] + " " + line.strip()
        elif out and not ROW_TAIL.search(out[-1]):
            out[-1] = out[-1] + " " + line.strip()
        else:
            out.append(line)
    return out


def parse_row(line, current_molecule, current_section):
    """Return (record, molecule, section) — record is None if the row is not priced."""
    tail = ROW_TAIL.search(line)
    if not tail:
        return None, current_molecule, current_section

    price = float(tail.group(1).replace(",", ""))
    notification = tail.group(2).strip()
    date = tail.group(3)
    head = line[: tail.start()].strip()

    # New molecule? The row opens with an NLEM section number.
    sec = re.match(r"^(\d+(?:\.\d+)+)\s+(.*)$", head)
    if sec:
        current_section = sec.group(1)
        rest = sec.group(2)
        # Molecule name runs until the dosage form begins
        cut = len(rest)
        low = rest.lower()
        for w in DOSAGE_WORDS:
            i = low.find(w)
            if i > 0:
                cut = min(cut, i)
        current_molecule = rest[:cut].strip(" ,-")
        formulation = rest[cut:].strip()
    else:
        formulation = head.strip()
        # A continuation row must belong to the molecule above it. If the row
        # carries no formulation text at all, record it as unknown rather than
        # inheriting the previous row's, which produced "Oxygen ... Injection".
        if not formulation:
            formulation = None

    if not current_molecule:
        return None, current_molecule, current_section

    # Split formulation into dosage form/strength and unit/pack
    pack = None
    m = re.search(r"(Each Pack[^,]*|1 Tablet|1 Capsule|1 ml|1 gm|1 vial|\d+\s*(?:ml|gm|g)\b)\s*$",
                  formulation, re.IGNORECASE)
    if m:
        pack = m.group(1).strip()
        formulation = formulation[: m.start()].strip()

    return ({
        "molecule": current_molecule,
        "nlem_section": current_section,
        "formulation": formulation or None,
        "pack": pack,
        "ceiling_price_inr": price,
        "notification_no": notification,
        "notification_date": date,
    }, current_molecule, current_section)


def parse_pdf(path):
    import pypdf
    reader = pypdf.PdfReader(path)
    records, unparsed = [], []
    molecule = section = None
    for page in reader.pages:
        text = page.extract_text() or ""
        for line in join_wrapped(text.split("\n")):
            if re.search(r"ceiling price|dosage form|s\.o\. no", line, re.IGNORECASE):
                continue                                    # header
            rec, molecule, section = parse_row(line, molecule, section)
            if rec:
                records.append(rec)
            elif re.search(r"\d+\.\d{2}", line) and len(line) > 30:
                unparsed.append(line.strip()[:160])
    return records, unparsed


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    path = args.pdf
    if not path:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".nppa_compendium.pdf")
        if not os.path.exists(path):
            print("Downloading NPPA Compendium of Prices…")
            download(path)

    print(f"Parsing {path}")
    records, unparsed = parse_pdf(path)
    molecules = {r["molecule"] for r in records}
    print(f"  {len(records)} priced formulations across {len(molecules)} molecules")
    print(f"  {len(unparsed)} line(s) with a number that did not parse (recorded, not guessed)")

    if args.dry_run:
        for r in records[:12]:
            print(f"    {r['molecule'][:26]:28} {str(r['formulation'])[:30]:32} "
                  f"Rs{r['ceiling_price_inr']:>9}  {r['notification_no']} {r['notification_date']}")
        return

    if not MONGO_URL:
        raise SystemExit("MONGO_URL is not set.")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    await db.ceiling_prices.delete_many({})
    if records:
        for r in records:
            r.update({
                "source_name": SOURCE_NAME,
                "source_url": SOURCE_PAGE,
                "source_pdf": PDF_URL,
                "retrieved_utc": stamp,
                "price_basis": "statutory ceiling under DPCO 2013",
            })
        await db.ceiling_prices.insert_many(records)
    await db.ceiling_price_unparsed.delete_many({})
    if unparsed:
        await db.ceiling_price_unparsed.insert_many(
            [{"line": u, "retrieved_utc": stamp} for u in unparsed])

    # How much of our own catalogue does this cover?
    ours = [d["name"] async for d in db.drugs.find({}, {"_id": 0, "name": 1})]
    ceiling_lower = {m.lower() for m in molecules}
    matched = [n for n in ours
               if any(tok and tok in cl
                      for cl in ceiling_lower
                      for tok in [re.split(r"[^a-z]+", n.lower())[0]] if len(tok) > 4)]
    print(f"\n✅ loaded {len(records)} ceiling prices into '{DB_NAME}'.ceiling_prices")
    print(f"   covers {len(set(matched))}/{len(ours)} molecules in the catalogue")
    print(f"   {len(unparsed)} unparsed lines kept in ceiling_price_unparsed for review")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
