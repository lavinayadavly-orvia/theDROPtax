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
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# "  12. Letermovir Bulk Drug ... 17.01.2025"
ROW_START = re.compile(r"^\s*(\d{1,4})\s*\.\s*(.*)$")
DATE = re.compile(r"(\d{2})[.\-/](\d{2})[.\-/](\d{4})")
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
    # A PDF with no extractable text is a scan. It needs OCR, and must be
    # reported as unread rather than counted as an empty list.
    if len(text.strip()) < 40:
        raise ValueError("no extractable text — scanned image, needs OCR")

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
    def scan(require_period: bool):
        pattern = (r"(?<![\d.])(\d{1,4})\s*\.\s+(?=[A-Za-z])" if require_period
                   else r"(?<![\d.])(\d{1,4})\s*\.?\s+(?=[A-Z][a-z])")
        expected, found = 1, []
        for m in re.finditer(pattern, text):
            if int(m.group(1)) == expected:
                found.append((m.start(), expected, m.end()))
                expected += 1
        return found

    marks = scan(True)
    mode = "numbered"
    if len(marks) < 3:
        loose = scan(False)
        if len(loose) > len(marks):
            marks, mode = loose, "unnumbered"

    blocks = []
    for i, (start, serial, body_at) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        blocks.append({"serial": serial, "parts": [text[body_at:end]]})

    records, unparsed = [], 0
    for b in blocks:
        body = re.sub(r"\s+", " ", " ".join(b["parts"])).strip()
        if len(body) < 4:
            continue
        d = DATE.search(body)
        approval_date = None
        if d:
            dd, mm, yyyy = d.groups()
            try:
                approval_date = datetime(int(yyyy), int(mm), int(dd)).date().isoformat()
            except ValueError:
                approval_date = None
        without_date = DATE.sub(" ", body).strip(" .")

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
            "name_split_confident": confident,
            "raw": body[:900],
            "source_list": source_title,
            "source_url": source_url,
            "parse_mode": mode,
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


if __name__ == "__main__":
    asyncio.run(main())
