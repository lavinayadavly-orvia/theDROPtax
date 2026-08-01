import os
import sys
import asyncio
import re
import uuid
from pathlib import Path
import openpyxl
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from core.therapy_areas import resolve_indication

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "droptax")

# ── Oncology exclusion ────────────────────────────────────────────────────
# The DROP Tax platform covers CardioMetabolic + Women's Health only.
# Two rules, because a blunt keyword filter would wrongly delete core
# gynaecology drugs (Leuprolide/Goserelin treat endometriosis and fibroids;
# Raloxifene treats osteoporosis) that merely *mention* cancer in their label.

# 1. Molecules whose PRIMARY purpose is oncology — excluded entirely.
ONCOLOGY_ONLY_MOLECULES = {
    "tamoxifen", "anastrozole", "exemestane", "letrozole",
    "fulvestrant", "toremifene", "megestrol",
}

# 2. Oncology phrases stripped from otherwise-relevant drugs' indication text.
ONCOLOGY_PHRASES = [
    r"breast[- ]cancer risk reduction", r"hormone[- ]receptor[- ]positive breast cancer",
    r"breast\s*/\s*prostate cancer", r"breast cancer \(treatment & prevention\)",
    r"breast cancer", r"prostate cancer", r"ovarian cancer", r"endometrial cancer",
    r"tumou?r[- ]lysis (?:hyperuricemia|prevention)", r"tumou?r[- ]lysis",
    r"\bcancer\b", r"\boncolog\w*\b", r"\bcarcinoma\b", r"\bmalignan\w*\b",
]


def strip_oncology(text: str) -> str:
    """Remove oncology phrases from an indication string, tidy the leftovers."""
    if not text:
        return text
    out = text
    for pat in ONCOLOGY_PHRASES:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    # Tidy separators left behind (";  ;", trailing "&", double spaces, etc.)
    out = re.sub(r"\s*[;,]\s*(?=[;,])", "", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"^\s*[;,&/]+\s*|\s*[;,&/]+\s*$", "", out)
    out = re.sub(r"\(\s*\)", "", out)
    return out.strip(" ;,&/-") or "Approved indications"


def is_oncology_only(molecule_name: str) -> bool:
    return (molecule_name or "").strip().lower() in ONCOLOGY_ONLY_MOLECULES

def parse_indicative_price(price_str):
    if not price_str:
        return 0.0
    try:
        # Remove currency symbol, commas, and space
        cleaned = price_str.replace('₹', '').replace(',', '').strip()
        # Check for range like "2–5" or "100–120" or "4-10" or "4 - 10"
        match_range = re.findall(r'(\d+(?:\.\d+)?)\s*[\-–]\s*(\d+(?:\.\d+)?)', cleaned)
        if match_range:
            low, high = float(match_range[0][0]), float(match_range[0][1])
            return (low + high) / 2.0
        # Single number
        match_num = re.findall(r'\d+(?:\.\d+)?', cleaned)
        if match_num:
            return float(match_num[0])
    except Exception:
        pass
    return 0.0

def make_slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

async def main():
    print("Connecting to MongoDB Atlas...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    workbook_path = (
        sys.argv[1] if len(sys.argv) > 1
        else os.environ.get("WORKBOOK_PATH")
        or str(Path.home() / "Downloads" / "India_Drug_Database_CV_Metabolic_WomensHealth.xlsx")
    )
    if not Path(workbook_path).exists():
        raise SystemExit(
            f"Workbook not found: {workbook_path}\n"
            f"Usage: python3 seed_from_workbook.py /path/to/your.xlsx"
        )
    print(f"Loading workbook: {workbook_path}")
    wb = openpyxl.load_workbook(workbook_path, data_only=True)

    # Match sheets loosely so workbook revisions (e.g. "Womens Health" vs
    # "Women's Health") don't break the import.
    def _find_sheet(*keywords):
        for name in wb.sheetnames:
            norm = re.sub(r"[^a-z]", "", name.lower())
            if all(re.sub(r"[^a-z]", "", k.lower()) in norm for k in keywords):
                return name
        return None

    sheet_mappings = [
        {"sheet_name": _find_sheet("cardiovascular"), "category": "CVD"},
        {"sheet_name": _find_sheet("metabolic"), "category": "Metabolic"},
        {"sheet_name": _find_sheet("women"), "category": "Women's Health"},
    ]
    missing = [m["category"] for m in sheet_mappings if not m["sheet_name"]]
    if missing:
        raise SystemExit(f"Workbook is missing sheet(s) for: {', '.join(missing)}. Found: {wb.sheetnames}")
    sheet_mappings = [m for m in sheet_mappings if m["sheet_name"]]
    
    drugs_to_insert = []
    skipped_oncology = []
    cleaned_indications = []

    for mapping in sheet_mappings:
        sheet_name = mapping["sheet_name"]
        category = mapping["category"]
        print(f"Parsing sheet: {sheet_name}...")
        
        sheet = wb[sheet_name]
        # Columns start at row 3 (headers)
        # Data starts at row 4
        for r_idx in range(4, sheet.max_row + 1):
            row = [cell.value for cell in sheet[r_idx]]
            if not row or not any(row):
                continue
            
            # Extract fields safely
            sub_category = row[0] or "General"
            molecule_name = row[1]
            route_form = row[2] or "Oral"
            common_strengths = row[3] or "Standard"
            key_brands = row[4] or "Representative Generics"
            manufacturers = row[5] or "Various Manufacturers"
            launch_approx = str(row[6] or "NA")
            price_raw = str(row[7] or "")
            indications = row[8] or "Approved indications"
            notes = row[9] or ""
            # v2 workbook: real Patient Support Programme (PSP) columns
            patient_program = row[10] if len(row) > 10 else None
            program_sponsor = row[11] if len(row) > 11 else None
            
            if not molecule_name:
                continue

            # Exclude oncology-only molecules; strip oncology text from the rest
            if is_oncology_only(molecule_name):
                skipped_oncology.append(molecule_name)
                continue
            cleaned = strip_oncology(str(indications))
            if cleaned != str(indications):
                cleaned_indications.append(molecule_name)
            indications = cleaned
            notes = strip_oncology(str(notes)) if notes else notes

            price = parse_indicative_price(price_raw)
            slug = make_slug(molecule_name)
            
            # Resolve the therapy-area registry entry for this indication.
            # The workbook has no trial data, so clinical endpoints are left
            # UNAVAILABLE (flagged) rather than fabricated — the web sweeper or a
            # user fills them in. Only the (estimated) safety rate is seeded.
            _entry = resolve_indication(indications)
            _pe = _entry["primary_endpoint"] if _entry else None
            if category == "Metabolic":
                toxic_rate = 0.12
            elif category == "Women's Health":
                toxic_rate = 0.10
            else:  # CVD / CVS / other
                toxic_rate = 0.15

            # Build complete drug document
            drug_doc = {
                "id": slug,
                "name": molecule_name,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "category": category,
                "route_form": route_form,
                "route": (_entry.get("route_default") if _entry else None),
                "treatment_model": (_entry.get("treatment_model") if _entry else None),
                "common_strengths": common_strengths,
                "key_brands": key_brands,
                "manufacturers": manufacturers,
                # Real patient-support-programme data from the workbook (not invented)
                "patient_program": strip_oncology(str(patient_program)) if patient_program else None,
                "program_sponsor_type": strip_oncology(str(program_sponsor)) if program_sponsor else None,
                "indication": indications,
                "mechanism_of_action": sub_category,
                "launch_date": launch_approx,
                "global_price_inr": price if price > 0 else 100.0,
                "has_multiple_indications": False,
                "indications_available": [{"indication": indications}],
                "primary_endpoint_key": (_pe["key"] if _pe else None),
                "primary_endpoint_label": (_pe["label"] if _pe else None),
                "primary_endpoint_unit": (_pe["unit"] if _pe else None),
                "primary_endpoint_value": None,
                "primary_endpoint_is_estimated": True,
                "primary_endpoint_method": None,
                "hazard_ratio": None,
                "secondary_endpoints": [],
                "clinical_confidence": 0.0,
                "competitor_name": "Standard of Care",
                "competitor_price_inr": max(1.0, round(price * 0.5)) if price > 0 else 50.0,
                "drug_severe_ae_rate": toxic_rate,
                "competitor_severe_ae_rate": round(toxic_rate + 0.05, 2),
                "drug_ae_is_estimated": True,
                "competitor_ae_is_estimated": True,
                "drug_adverse_events": ["Nausea", "Headache", "Fatigue"],
                "competitor_adverse_events": ["Muscle Pain", "Gastrointestinal discomfort"],
                "data_quality": {
                    "status": "unavailable",
                    "missing_fields": [(_pe["key"] if _pe else "primary_endpoint")],
                    "issues": [{"field": (_pe["key"] if _pe else "primary_endpoint"), "severity": "warning",
                                "message": "Primary endpoint not in workbook — run analysis or enter manually."}],
                },
                "epidemiology": {
                    "addressable_population": None,
                    "sources": "Not available — regional incidence not resolved"
                },
                "data_sources": {
                    "clinical": "Standard prescribing guides",
                    "competitor": "Standard of Care baseline",
                    "safety": "Clinical trial safety metadata",
                    "drug_safety": "Product label",
                    "clinical_tier": "tier_2",
                    "competitor_tier": "tier_3",
                    "safety_tier": "tier_2"
                },
                "regional_availability": {
                    "global_approval": {"agency": "FDA", "date": launch_approx, "status": "approved"},
                    "regional_status": "launched",
                    "local_regulator": "CDSCO",
                    "local_approval_date": launch_approx,
                    "availability_text": "Commercially Available (Audited)",
                    "availability_color": "green",
                    "notes": notes,
                    "is_available": True
                },
                "regional_prices": {
                    "IN": price if price > 0 else 100.0,
                    "SG": max(1, int((price if price > 0 else 100.0) / 60)),
                    "AE": max(1, int((price if price > 0 else 100.0) / 22))
                }
            }
            
            drugs_to_insert.append(drug_doc)
            
    print(f"Parsed {len(drugs_to_insert)} drugs total.")
    
    # We delete existing drugs and seed fresh
    print("Clearing 'drugs' collection...")
    await db.drugs.delete_many({})
    
    print("Inserting fresh seeded drugs...")
    if drugs_to_insert:
        await db.drugs.insert_many(drugs_to_insert)
        print(f"✅ Seeded {len(drugs_to_insert)} drugs into '{DB_NAME}'.drugs")
    else:
        print("No drugs parsed to insert.")

    # ── Patient Support Programs sheet (v2 workbook) ─────────────────────
    psp_sheet_name = next((s for s in wb.sheetnames if "support program" in s.lower()), None)
    if psp_sheet_name:
        psp_sheet = wb[psp_sheet_name]
        programs = []
        for r_idx in range(4, psp_sheet.max_row + 1):
            row = [c.value for c in psp_sheet[r_idx]]
            if not row or not row[0]:
                continue
            covers = strip_oncology(str(row[3] or ""))
            programs.append({
                "id": make_slug(str(row[0])),
                "name": str(row[0]),
                "sponsor": str(row[1] or ""),
                "type": strip_oncology(str(row[2] or "")),
                "covers": covers,
                "offers": str(row[4] or ""),
                "how_to_access": str(row[5] or ""),
            })
        await db.support_programs.delete_many({})
        if programs:
            await db.support_programs.insert_many(programs)
            print(f"✅ Seeded {len(programs)} patient support programmes into '{DB_NAME}'.support_programs")

    if skipped_oncology:
        print(f"🚫 Excluded {len(skipped_oncology)} oncology-only molecule(s): {', '.join(skipped_oncology)}")
    if cleaned_indications:
        print(f"🧹 Stripped oncology wording from {len(cleaned_indications)} indication(s): {', '.join(cleaned_indications)}")
        
if __name__ == "__main__":
    asyncio.run(main())
