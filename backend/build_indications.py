"""
Structure every catalogue row's indication prose into discrete indications.

The platform reasons about (drug x indication), not drug: ramipril for
hypertension and ramipril for high cardiovascular risk rest on different trials
and answer different questions at the same price. Until this runs, 299
indications sit inside 218 free-text strings and nothing downstream can branch
on them.

Rows are updated by their own _id, never by name. Nifedipine and spironolactone
each occupy two rows with DIFFERENT indication text, and a name-keyed update
would overwrite one row with the other's indications — the same defect that
left two rows with no NLEM verdict.

Usage
-----
    python3 build_indications.py --dry-run     # report, change nothing
    python3 build_indications.py               # write
"""
import os
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from core.indications import structure

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "droptax")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", type=int, default=10)
    args = ap.parse_args()

    if not MONGO_URL:
        raise SystemExit("MONGO_URL is not set.")
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    rows = [d async for d in db.drugs.find({}, {"_id": 1, "name": 1, "indication": 1})]
    total_ind = 0
    multi = 0
    unmapped = Counter()
    no_indication = []
    shown = 0

    for d in rows:
        s = structure(d.get("indication"))
        total_ind += s["indication_count"]
        multi += 1 if s["has_multiple_indications"] else 0
        for u in s["unmapped"]:
            unmapped[u] += 1
        if s["indication_count"] == 0:
            no_indication.append(d.get("name"))

        if shown < args.show and s["has_multiple_indications"]:
            names = " · ".join(
                f"{i['text']}{'*' if not i['mapped'] else ''}" for i in s["indications"])
            print(f"  {str(d.get('name'))[:20]:22} {names[:88]}")
            shown += 1

        if not args.dry_run:
            await db.drugs.update_one({"_id": d["_id"]}, {"$set": {
                **s, "indications_structured_utc": stamp}})

    print(f"\n  {len(rows)} rows -> {total_ind} indications")
    print(f"  {multi} rows carry more than one indication")
    print(f"  {total_ind - sum(unmapped.values())} mapped to the registry, "
          f"{sum(unmapped.values())} unmapped (kept, marked, not forced)")
    if no_indication:
        print(f"  {len(no_indication)} row(s) with no indication at all: "
              f"{', '.join(str(n) for n in no_indication[:6])}")

    print("\n  most frequent unmapped indications — registry gaps worth filling:")
    for name, n in unmapped.most_common(12):
        print(f"    x{n:<3} {name[:64]}")

    if args.dry_run:
        print("\n  (dry run — nothing written)")
    else:
        print(f"\n  written to '{DB_NAME}'.drugs")


if __name__ == "__main__":
    asyncio.run(main())
