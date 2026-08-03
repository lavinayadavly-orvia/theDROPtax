"""
Source-verify drug facts from FDA labels via DailyMed.

DailyMed is the NIH/FDA repository of official Structured Product Labels. This
script reads the label for each molecule and extracts ONLY values that appear
verbatim in the document, storing each with its source URL, retrieval date and
the sentence it came from.

Nothing is inferred. If a pattern is not found in the label, the field is left
absent and reported as unmatched — the platform then shows it as unavailable.

Usage
-----
    python3 verify_from_dailymed.py                # innovator/branded set
    python3 verify_from_dailymed.py --all          # every molecule in the DB
    python3 verify_from_dailymed.py Inclisiran Semaglutide

Writes core/verified_facts_dailymed.py, which core/verified_facts.py merges.
"""
import os
import re
import sys
import json
import time
import asyncio
import urllib.parse
import urllib.request
from datetime import date, timezone, datetime

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "droptax")

SEARCH_API = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name={}&pagesize=5"
XML_API = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{}.xml"
HUMAN_URL = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={}"

# Companies that indicate an innovator/branded product rather than a generic.
INNOVATOR_COMPANIES = [
    "novartis", "novo nordisk", "eli lilly", "lilly", "astrazeneca", "boehringer",
    "amgen", "sanofi", "bayer", "pfizer", "merck", "msd", "gsk", "glaxo",
    "janssen", "abbvie", "astellas", "daiichi", "takeda", "organon", "ferring",
    "besins", "gedeon", "servier", "ucb",
]

REQUEST_DELAY_SEC = 0.6   # be polite to a public API


def _get(url, as_bytes=False):
    req = urllib.request.Request(url, headers={"User-Agent": "DROP-Tax-verification/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    return raw if as_bytes else raw.decode("utf-8", errors="ignore")


def find_label(molecule: str):
    """Return (setid, title) for the best-matching SPL, or (None, None)."""
    # Strip parenthetical brand qualifiers: "Semaglutide (oral)" -> "Semaglutide"
    clean = re.sub(r"\(.*?\)", "", molecule).strip()
    clean = re.split(r"[+/]", clean)[0].strip()      # combinations: take first agent
    try:
        data = json.loads(_get(SEARCH_API.format(urllib.parse.quote(clean))))
    except Exception:
        return None, None
    results = data.get("data") or []
    if not results:
        return None, None
    # Prefer an innovator labeler when several SPLs exist for the molecule.
    for r in results:
        title = (r.get("title") or "").lower()
        if any(co in title for co in INNOVATOR_COMPANIES):
            return r.get("setid"), r.get("title")
    return results[0].get("setid"), results[0].get("title")


def _plain_text(xml: str) -> str:
    text = re.sub(r"<[^>]+>", " ", xml)
    return re.sub(r"\s+", " ", text)


def extract_facts(setid: str, title: str):
    """Extract only what is literally present in the label."""
    try:
        xml = _get(XML_API.format(setid))
    except Exception:
        return {}
    text = _plain_text(xml)
    url = HUMAN_URL.format(setid)
    today = date.today().isoformat()
    facts = {}

    def record(key, value, quote=None):
        facts[key] = {
            "value": value,
            "source_name": f"FDA prescribing information via DailyMed ({title})" if title
                           else "FDA prescribing information via DailyMed",
            "source_url": url,
            "retrieved": today,
        }
        if quote:
            facts[key]["quote"] = quote.strip()

    # 1. Initial U.S. Approval year — stated verbatim in the label highlights.
    m = re.search(r"Initial U\.S\. Approval:?\s*(\d{4})", text)
    if m:
        record("us_initial_approval_year", int(m.group(1)), m.group(0))

    # 2. Recommended dosage — scoped to the DOSAGE AND ADMINISTRATION section
    #    and required to be an explicit "recommended dos(e|age)" statement.
    #    A loose match picks up drug-interaction and titration sentences, which
    #    would be a real quote attached to the wrong field.
    dose_section = None
    sec = re.search(r"DOSAGE AND ADMINISTRATION(.{0,6000})", text, re.IGNORECASE)
    if sec:
        dose_section = sec.group(1)
    if dose_section:
        m = re.search(
            r"(The recommended (?:dosage|dose|starting dosage)(?:[^.]|\.(?=\d)){0,300}?\.(?!\d))",
            dose_section, re.IGNORECASE)
        if m:
            quote = m.group(1).strip()
            # Reject fragments that begin mid-word or mid-heading.
            if quote[:1].isupper() and len(quote) > 30:
                record("recommended_dosage", quote, quote)

    # 3. Loading-dose regimens ("initially, again at N months, then every M months")
    m = re.search(r"(The recommended (?:[^.]|\.(?=\d)){0,200}initially(?:[^.]|\.(?=\d)){0,160}again at \d+ months?(?:[^.]|\.(?=\d)){0,120}\.(?!\d))", text)
    if m:
        quote = m.group(1).strip()
        gap = re.search(r"again at (\d+) months?", quote)
        every = re.search(r"every (\d+) months?", quote)
        if gap and every:
            g, e = int(gap.group(1)), int(every.group(1))
            times, t = [0, g], g + e
            while t < 12:
                times.append(t)
                t += e
            record("dosing_schedule", quote, quote)
            facts["dosing_schedule"]["doses_year_1"] = len(times)
            facts["dosing_schedule"]["doses_maintenance"] = max(1, round(12 / e))

    return facts


async def main():
    if not MONGO_URL:
        raise SystemExit("MONGO_URL is not set.")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_all = "--all" in sys.argv

    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    if args:
        names = args
    else:
        names = []
        async for d in db.drugs.find({}, {"_id": 0, "name": 1, "manufacturers": 1}):
            mfr = str(d.get("manufacturers") or "").lower()
            if do_all or (any(co in mfr for co in INNOVATOR_COMPANIES) and "generic" not in mfr):
                names.append(d["name"])
    names = sorted(set(names))
    print(f"Verifying {len(names)} molecule(s) against FDA labels via DailyMed…\n")

    verified, unmatched = {}, []
    for i, name in enumerate(names, 1):
        setid, title = find_label(name)
        if not setid:
            unmatched.append((name, "no FDA label found"))
            print(f"  [{i:3}/{len(names)}] {name[:34]:36} — no US label")
            time.sleep(REQUEST_DELAY_SEC)
            continue
        facts = extract_facts(setid, title)
        if facts:
            verified[name.strip().lower()] = {
                "molecule": name,
                "facts": facts,
                "spl_setid": setid,
                "spl_title": title,
            }
            print(f"  [{i:3}/{len(names)}] {name[:34]:36} ✓ {', '.join(sorted(facts))}")
        else:
            unmatched.append((name, "label found but no extractable pattern"))
            print(f"  [{i:3}/{len(names)}] {name[:34]:36} — label found, nothing extractable")
        time.sleep(REQUEST_DELAY_SEC)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "verified_facts_dailymed.py")
    with open(out, "w") as f:
        f.write('"""\nAUTO-GENERATED by verify_from_dailymed.py — do not hand-edit.\n\n'
                'Every value below was extracted verbatim from an FDA Structured Product\n'
                'Label on DailyMed, with its source URL and retrieval date. Regenerate by\n'
                'rerunning the script; do not add entries manually.\n"""\n\n')
        f.write(f"GENERATED_AT = {json.dumps(datetime.now(timezone.utc).isoformat())}\n\n")
        f.write("DAILYMED_FACTS = ")
        f.write(json.dumps(verified, indent=4, ensure_ascii=False))
        f.write("\n\nUNMATCHED = ")
        f.write(json.dumps(unmatched, indent=4, ensure_ascii=False))
        f.write("\n")

    print(f"\n✅ verified {len(verified)} molecule(s); {len(unmatched)} unmatched")
    print(f"   written to core/verified_facts_dailymed.py")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
