"""
Build the India approval register from CDSCO.

openFDA answers a United States question. It is useful here only as a pipeline
signal — approved there means it will probably reach India eventually, not
approved there means it may never arrive — and it says nothing about what is
actually available, approved, or competed here. Tenecteplase is exclusive to
Genentech in Drugs@FDA and sold in India by Emcure as Elaxim. Reading US
exclusivity as Indian exclusivity produces confident false statements.

CDSCO publishes the real thing: every new drug approved in India, with the
indication it was approved FOR and the date, year by year from 2000.

Source
------
cdsco.gov.in -> Approvals -> List of Approved New Drugs, 40 year-wise lists.

Getting at them took three wrong turns worth recording, because each looked
like success:

1. /en/Drugs/New-Drugs/ is guidance, not data.
2. The listing table is a DataTable, so searching the HTML for .pdf links
   returns nothing. The rows are server-rendered though, and all 40 num_id
   tokens ARE in the static HTML — the links just point at a jsp, not a file.
3. That jsp returns 319 bytes of HTML wrapping an <iframe>, not the PDF. The
   real file path is inside it, typos and all ("...till datee.pdf").

Nothing is inferred from a row that does not parse. A row is recorded with
whatever could be read from it and a flag saying what could not, because a
drug missing from this register must read as "not found in CDSCO" and never
as "not approved in India".

Usage
-----
    python3 build_cdsco_db.py --dry-run          # parse, print, load nothing
    python3 build_cdsco_db.py --years 2023 2026  # a subset
    python3 build_cdsco_db.py                    # everything, then load
"""
import os
import re
import ssl
import base64
import argparse
import asyncio
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "droptax")

SOURCE_NAME = "CDSCO List of Approved New Drugs"
LISTING_URL = "https://cdsco.gov.in/opencms/opencms/en/Approval_new/Approved-New-Drugs/"
JSP = ("https://cdsco.gov.in/opencms/opencms/system/modules/"
       "CDSCO.WEB/elements/download_file_division.jsp?num_id=")
HOST = "https://cdsco.gov.in"
MIN_ROW_CHARS = 40      # see scan(): shorter gaps are numbered indications
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# "  12. Letermovir Bulk Drug ... 17.01.2025"
ROW_START = re.compile(r"^\s*(\d{1,4})\s*\.\s*(.*)$")
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
# Four date forms appear across 25 years of lists. Matching only dd.mm.yyyy
# left 513 of 733 rows undated, including every row in the older lists, which
# write "October-1985".
DATE_FORMS = [
    re.compile(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\b"),                    # 16.01.2025
    re.compile(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2})\b"),                    # 16.01.25
    re.compile(r"\b(\d{1,2})[ \-]([A-Za-z]{3,9})[ \-](\d{2,4})\b"),              # 16-Jan-2025
    re.compile(r"\b([A-Za-z]{3,9})[ \-](\d{4})\b"),                              # October-1985
]
ANY_DATE = re.compile(
    r"\b\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}\b"
    r"|\b\d{1,2}[ \-][A-Za-z]{3,9}[ \-]\d{2,4}\b"
    r"|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[ \-]\d{4}\b",
    re.IGNORECASE)


def parse_date(text):
    """First readable date in a row, or None. Never a guess.

    A month-and-year with no day is real information and is kept, dated to the
    first of that month with day_known False, rather than discarded.
    """
    for i, pat in enumerate(DATE_FORMS):
        m = pat.search(text)
        if not m:
            continue
        try:
            if i == 0:
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            elif i == 1:
                d, mo, y = int(m.group(1)), int(m.group(2)), 2000 + int(m.group(3))
                if y > datetime.now().year:
                    y -= 100
            elif i == 2:
                mo = MONTHS.get(m.group(2)[:3].lower())
                if not mo:
                    continue
                d, y = int(m.group(1)), int(m.group(3))
                y = y + 1900 if y < 100 and y > 50 else (y + 2000 if y < 100 else y)
            else:
                mo = MONTHS.get(m.group(1)[:3].lower())
                if not mo:
                    continue
                d, y = 1, int(m.group(2))
            if not (1900 <= y <= datetime.now().year + 1):
                continue
            return datetime(y, mo, d).date().isoformat(), (i != 3)
        except (ValueError, TypeError):
            continue
    return None, False
# Where the drug name stops and the indication begins. No delimiter exists, so
# these are the phrases that actually open an indication in this register.
INDICATION_START = re.compile(
    r"\b(is indicated|are indicated|indicated for|indicated in|not applicable|"
    r"for the treatment|for treatment|in patients|as an adjunct|for prophylaxis|"
    r"for the prophylaxis|for use in|to reduce|to treat)\b", re.IGNORECASE)


def _ctx():
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE          # cdsco.gov.in serves an incomplete chain
    return c


def http_get(url, timeout=90, referer=None):
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
        return r.read()


def fetch_listing():
    """The 40 year-wise lists: (num_id token, title, release date).

    Rows are server-rendered, so the static HTML carries everything. The
    DataTable only adds paging on top.
    """
    html = http_get(LISTING_URL).decode("utf-8", "replace")
    rows = []
    for m in re.finditer(
            r"<tr[^>]*>.*?<td[^>]*>\s*(\d+)\s*</td>\s*<td[^>]*>(.*?)</td>\s*"
            r"<td[^>]*>(.*?)</td>.*?num_id=([A-Za-z0-9+/=]+)", html, re.S):
        title = re.sub(r"<[^>]+>", " ", m.group(2))
        title = re.sub(r"\s+", " ", title).strip()
        released = re.sub(r"<[^>]+>", " ", m.group(3)).strip()
        rows.append({"title": title, "released": released, "num_id": m.group(4)})
    return rows


def resolve_pdf_url(num_id):
    """The jsp returns an iframe wrapping the real static path, not the file."""
    body = http_get(JSP + num_id, referer=LISTING_URL).decode("utf-8", "replace")
    m = re.search(r"src='([^']+\.pdf)'", body) or re.search(r'src="([^"]+\.pdf)"', body)
    if not m:
        m = re.search(r"<!--\s*(/[^\s]+\.pdf)\s*-->", body)
    if not m:
        return None
    return HOST + urllib.parse.quote(m.group(1))


def year_of(title):
    m = re.search(r"(19|20)\d{2}", title or "")
    return int(m.group(0)) if m else None


def _records_from_ocr_rows(rows, source_title, source_url):
    """Approvals from OCR rows, which are already row-grouped left to right.

    A row is kept when it carries a date or reads like a drug entry. The serial
    is whatever leading integer the row starts with, and its absence is not
    fatal — OCR merges the header cell into row one often enough that insisting
    on it loses the row.
    """
    out = []
    for row in rows:
        body = re.sub(r"\s+", " ", row["text"]).strip()
        if len(body) < 12:
            continue
        low = body.lower()
        if any(h in low for h in ("s.no", "name of drug", "pharmacological",
                                  "date of approval", "list of drug")) and len(body) < 90:
            continue
        approval_date, day_known = parse_date(body)
        without_date = re.sub(r"\s+", " ", ANY_DATE.sub(" ", body)).strip(" .,-")
        serial = None
        m = re.match(r"^\s*(\d{1,4})\s+", without_date)
        if m:
            serial = int(m.group(1))
            without_date = without_date[m.end():]
        split = INDICATION_START.search(without_date)
        if split and split.start() > 2:
            name = without_date[: split.start()].strip(" ,;-")
            indication = without_date[split.start():].strip(" ,;-")
            confident = True
        else:
            name, indication, confident = without_date.strip(), None, False
        if not name or (approval_date is None and not confident and len(name) < 20):
            continue
        out.append({
            "serial": serial,
            "drug_name": name[:300] or None,
            "indication": indication[:600] if indication else None,
            "approval_date": approval_date,
            "approval_day_known": day_known,
            "name_split_confident": confident,
            "raw": body[:900],
            "source_list": source_title,
            "source_url": source_url,
            "parse_mode": "ocr_rows",
            "from_ocr": True,
            # OCR misreads. The confidence travels with the row so a figure
            # lifted from a scan is visibly weaker than one from a text layer.
            "ocr_confidence": row.get("confidence"),
        })
    return out


def parse_approvals(pdf_path, source_title, source_url):
    """Rows out of one year's list.

    Layout wraps badly — a single approval can span eight lines with the date
    at the end — so rows are accumulated from one serial number to the next
    rather than read line by line.
    """
    import pypdf
    reader = pypdf.PdfReader(pdf_path)
    text = re.sub(r"\s+", " ", "\n".join(
        (p.extract_text() or "") for p in reader.pages))
    # Nine of the forty lists are image tables with no text layer. Rather than
    # report them unread, fall back to OCR — macOS Vision, via ocr_pdf. Rows
    # are reassembled from bounding boxes because Vision returns a table
    # column-major, which as plain text is unreadable.
    #
    # OCR'd text is marked so a figure lifted from a scan is visibly weaker
    # evidence than one lifted from a text layer.
    ocred = False
    if len(text.strip()) < 40 or len(text) / max(os.path.getsize(pdf_path), 1) < 0.01:
        try:
            from ocr_pdf import ocr_pdf as _ocr
            ocr_rows, _stats = _ocr(pdf_path)
        except Exception as e:
            raise ValueError(f"no text layer and OCR failed: {e}")
        if ocr_rows:
            # OCR already grouped fragments into rows by bounding box, so the
            # row structure exists. Flattening it back to a string and hunting
            # serial numbers again throws that away and loses most of the rows —
            # the 2006 list gave 3 of its 40-odd approvals that way. Read the
            # rows directly instead.
            return _records_from_ocr_rows(ocr_rows, source_title, source_url), 0
    if len(text.strip()) < 40:
        raise ValueError("no extractable text and OCR produced nothing")

    # Rows are NOT line-delimited: extraction puts one row's date and the next
    # row's serial on the same line ("...17.01.2025 3. Fexuprazan..."), so a
    # per-line match finds a fraction of them and glues the rest together.
    #
    # Serials are sequential, and that is the reliable anchor. A candidate
    # "N." is accepted only when N is the number expected next, which makes
    # the scan self-correcting: "240 mg", "0.25/0.5/1/2/3/4 mg" and dates
    # cannot derail it because they are not the next serial.
    # Numbering is not consistent across 40 lists compiled over 25 years. Most
    # write "1. Drug"; several write "1 Drug" with no period, and those
    # returned zero rows under a pattern that required one. So the strict form
    # is tried first and the bare-number form only as a fallback, because
    # without the period "2 mg" can look like serial 2 — the sequential
    # constraint is doing more work in that mode, and which mode was used is
    # recorded rather than hidden.
    def scan(require_period: bool, start: int = 1):
        pattern = (r"(?<![\d.])(\d{1,4})\s*\.\s+(?=[A-Za-z])" if require_period
                   else r"(?<![\d.])(\d{1,4})\s*\.?\s+(?=[A-Z][a-z])")
        expected, found = start, []
        for m in re.finditer(pattern, text):
            if int(m.group(1)) != expected:
                continue
            # An indication can itself be numbered ("1. Acute bronchitis 2. ..."),
            # and early in a document those bullets collide with the serial the
            # scan is expecting. A real approval row is never a few characters
            # long, so a candidate sitting on top of the previous one is a
            # bullet, not a row.
            if found and m.start() - found[-1][0] < MIN_ROW_CHARS:
                continue
            found.append((m.start(), expected, m.end()))
            expected += 1
        return found

    # The scan does not insist on finding serial 1. On a scanned list OCR
    # routinely merges the header cell into the first data row, so "1" comes
    # back as "S.No" and a scan anchored at 1 finds nothing at all — which is
    # what happened to the 2006 list. Trying a few starting serials and keeping
    # whichever yields most rows costs nothing and survives a misread first row.
    best, mode = [], "numbered"
    for start in (1, 2, 3):
        got = scan(True, start)
        if len(got) > len(best):
            best = got
    if len(best) < 3:
        for start in (1, 2, 3):
            got = scan(False, start)
            if len(got) > len(best):
                best, mode = got, "unnumbered"
    marks = best

    blocks = []
    for i, (start, serial, body_at) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        blocks.append({"serial": serial, "parts": [text[body_at:end]]})

    records, unparsed = [], 0
    for b in blocks:
        body = re.sub(r"\s+", " ", " ".join(b["parts"])).strip()
        if len(body) < 4:
            continue
        approval_date, day_known = parse_date(body)
        without_date = re.sub(r"\s+", " ", ANY_DATE.sub(" ", body)).strip(" .,-")

        # Split name from indication at the phrase that opens an indication.
        # Where no such phrase appears the split is not guessed: the whole row
        # is kept as the name and the record says the split was not confident.
        split = INDICATION_START.search(without_date)
        if split and split.start() > 2:
            name = without_date[: split.start()].strip(" ,;-")
            indication = without_date[split.start():].strip(" ,;-")
            confident = True
        else:
            name, indication, confident = without_date.strip(), None, False

        if not approval_date and not confident:
            unparsed += 1

        records.append({
            "serial": b["serial"],
            "drug_name": name[:300] or None,
            "indication": indication[:600] if indication else None,
            "approval_date": approval_date,
            "approval_day_known": day_known,
            "name_split_confident": confident,
            "raw": body[:900],
            "source_list": source_title,
            "source_url": source_url,
            "parse_mode": mode,
            "from_ocr": ocred,
        })
    return records, unparsed


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--years", nargs=2, type=int, default=None,
                    help="inclusive range, e.g. --years 2023 2026")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cdsco")
    os.makedirs(cache, exist_ok=True)

    print(f"Fetching {LISTING_URL}")
    listing = fetch_listing()
    print(f"  {len(listing)} year-wise list(s) published\n")

    if args.years:
        lo, hi = args.years
        listing = [r for r in listing if (year_of(r["title"]) or 0) >= lo
                   and (year_of(r["title"]) or 9999) <= hi]
    if args.limit:
        listing = listing[: args.limit]

    all_records, total_unparsed = [], 0
    for row in listing:
        url = resolve_pdf_url(row["num_id"])
        if not url:
            print(f"  ! no file behind '{row['title'][:56]}' — skipped, not guessed")
            continue
        path = os.path.join(cache, base64.urlsafe_b64encode(
            row["num_id"].encode()).decode()[:40] + ".pdf")
        if not os.path.exists(path):
            try:
                data = http_get(url, referer=LISTING_URL)
            except Exception as e:
                print(f"  ! {row['title'][:48]}: {e}")
                continue
            if data[:4] != b"%PDF":
                print(f"  ! {row['title'][:48]}: not a PDF ({len(data)} bytes)")
                continue
            with open(path, "wb") as f:
                f.write(data)
        try:
            recs, unparsed = parse_approvals(path, row["title"], url)
        except Exception as e:
            print(f"  ! parse failed for {row['title'][:44]}: {e}")
            continue
        for r in recs:
            r["list_year"] = year_of(row["title"])
        all_records.extend(recs)
        total_unparsed += unparsed
        dated = sum(1 for r in recs if r["approval_date"])
        print(f"  {row['title'][:60]:62} {len(recs):>4} rows, {dated:>4} dated")

    print(f"\n  {len(all_records)} approvals parsed")
    print(f"  {sum(1 for r in all_records if r['approval_date'])} carry a date")
    print(f"  {sum(1 for r in all_records if r['name_split_confident'])} split "
          f"cleanly into name and indication")
    print(f"  {total_unparsed} row(s) with neither a date nor a clean split "
          f"(kept raw, not guessed at)")

    if args.dry_run:
        print("\n  sample:")
        for r in all_records[:8]:
            print(f"    {str(r['approval_date']):12} {str(r['drug_name'])[:44]:46} "
                  f"{str(r['indication'])[:46]}")
        print("\n  (dry run — nothing written)")
        return

    if not MONGO_URL:
        raise SystemExit("MONGO_URL is not set.")
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for r in all_records:
        r.update({"source_name": SOURCE_NAME, "retrieved_utc": stamp})
    await db.cdsco_approvals.delete_many({})
    if all_records:
        await db.cdsco_approvals.insert_many(all_records)
    print(f"\n✅ loaded {len(all_records)} CDSCO approvals into '{DB_NAME}'.cdsco_approvals")

    # Link every catalogue row to its Indian approval. Updated by _id, never by
    # name: nifedipine and spironolactone each occupy two rows.
    from core.india_approval import find_approvals
    found = combo_only = 0
    async for d in db.drugs.find({}, {"_id": 1, "name": 1}):
        a = find_approvals(d["name"], all_records)
        a["retrieved_utc"] = stamp
        if a["found"]:
            found += 1
            combo_only += 1 if a.get("only_as_combination") else 0
        await db.drugs.update_one({"_id": d["_id"]}, {"$set": {"india_approval": a}})
    total = await db.drugs.count_documents({})
    print(f"   linked: {found}/{total} molecules found in the register "
          f"({combo_only} only as a combination)")
    print(f"   the remaining {total - found} read 'not found in CDSCO', which is "
          f"NOT 'not approved in India'")


if __name__ == "__main__":
    asyncio.run(main())
