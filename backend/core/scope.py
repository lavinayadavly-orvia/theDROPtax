"""
What the platform covers, in one place.

CardioMetabolic and Women's Health. Oncology was removed from this codebase and
must not re-enter through a data source: the CDSCO r-DNA register is a quarter
oncology by volume — trastuzumab, cetuximab, pegfilgrastim — and loading it
whole put breast-cancer biologics back into a platform that had none.

Two rules, because a blunt keyword filter deletes drugs we need. Leuprolide and
goserelin treat endometriosis and fibroids, raloxifene treats osteoporosis, and
all three mention cancer in their labels. So a molecule is excluded on what it
IS, and text is judged only when the molecule is not already known to be ours.

Out of scope is recorded, not silently dropped. A user can type any drug, and
"this is outside what the platform covers" is a better answer than an empty one.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

# Molecules whose primary purpose is oncology. Small molecules from the
# workbook, plus the biologics that dominate the CDSCO r-DNA register.
ONCOLOGY_MOLECULES = {
    # hormonal / small molecule
    "tamoxifen", "anastrozole", "exemestane", "letrozole", "fulvestrant",
    "toremifene", "megestrol", "rasburicase",
    # biologics and biosimilars
    "trastuzumab", "pertuzumab", "bevacizumab", "rituximab", "cetuximab",
    "pembrolizumab", "nivolumab", "atezolizumab", "durvalumab", "ipilimumab",
    "daratumumab", "obinutuzumab", "ofatumumab", "ramucirumab", "panitumumab",
    "brentuximab", "blinatumomab", "elotuzumab", "isatuximab", "polatuzumab",
    "sacituzumab", "enfortumab", "tislelizumab", "sintilimab", "camrelizumab",
    "filgrastim", "pegfilgrastim", "lenograstim", "romiplostim", "eltrombopag",
    "asparaginase", "pegaspargase", "denileukin", "tebentafusp",
}

# Indication text that marks a row as oncology. Applied only when the molecule
# is not recognised, so it cannot strip a gynaecology drug that mentions cancer.
ONCOLOGY_INDICATION = re.compile(
    r"\b(cancer|carcinoma|oncolog\w*|malignan\w*|tumou?r|neoplas\w*|"
    r"lymphoma|leukaemia|leukemia|myeloma|sarcoma|melanoma|glioma|"
    r"metasta\w*|chemotherapy[- ]induced|myelosuppress\w*|neutropenia)\b",
    re.IGNORECASE)

# Molecules that mention cancer but are ours — never excluded on text.
PROTECTED_MOLECULES = {
    "leuprolide", "goserelin", "raloxifene", "denosumab", "tranexamic",
    "medroxyprogesterone", "megestrol acetate", "zoledronic",
}


def molecule_token(name: Optional[str]) -> str:
    """First word of a drug name, which is the molecule in these registers."""
    if not name:
        return ""
    token = re.split(r"[^A-Za-z]+", str(name).strip().lower())
    return token[0] if token and token[0] else ""


def is_oncology(drug_name: Optional[str],
                indication: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """(excluded, why). Text is judged only for unrecognised molecules."""
    token = molecule_token(drug_name)
    if not token:
        return False, None
    if token in PROTECTED_MOLECULES:
        return False, None
    if token in ONCOLOGY_MOLECULES:
        return True, f"{token} is an oncology molecule"
    # Some register rows name the molecule mid-string ("Recombinant Trastuzumab").
    lowered = (drug_name or "").lower()
    for known in ONCOLOGY_MOLECULES:
        if re.search(rf"\b{known}\b", lowered):
            return True, f"{known} is an oncology molecule"
    if indication:
        m = ONCOLOGY_INDICATION.search(indication)
        if m:
            return True, f"indication names {m.group(0).lower()}"
    return False, None
