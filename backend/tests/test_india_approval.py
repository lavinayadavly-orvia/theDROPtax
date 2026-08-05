"""
CDSCO parsing and molecule matching.

Two failure modes matter here and both produce confident wrong answers rather
than errors:

  - Substring matching returns a different product's approval. Searching raw
    row text for "ramipril" found a metoprolol-plus-atorvastatin combination.
  - Absence from the register reads as "not approved in India". It is not: the
    register is thin before about 2009 and nine of the forty lists are image
    tables with no text layer at all. Tenecteplase is sold here as Elaxim and
    does not appear.

The parser took three attempts to get right and had no test behind it, which is
what these are for.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from build_cdsco_db import parse_date, ANY_DATE
from core.india_approval import find_approvals, normalise


def _row(name, date=None, indication=None, **kw):
    r = {"drug_name": name, "approval_date": date, "indication": indication,
         "source_url": "https://cdsco.gov.in/x", "source_list": "test list"}
    r.update(kw)
    return r


# ── Dates ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected,day_known", [
    ("Edoxaban Tablets 11.02.2025", "2025-02-11", True),
    ("Some drug 16.01.25", "2025-01-16", True),
    ("Captopril October-1985", "1985-10-01", False),
    ("Approved 16-Jan-2025", "2025-01-16", True),
])
def test_every_date_form_in_the_register_is_read(text, expected, day_known):
    """Matching only dd.mm.yyyy left 513 of 733 rows undated — the older lists
    write 'October-1985'."""
    got, known = parse_date(text)
    assert got == expected and known is day_known


def test_a_month_and_year_is_kept_but_flagged_as_dayless():
    _, known = parse_date("Captopril October-1985")
    assert known is False, "a month-only date must not claim a known day"


def test_no_date_yields_none_not_today():
    assert parse_date("Tirzepatide 2.5mg solution for injection") == (None, False)


def test_implausible_years_are_refused():
    assert parse_date("Something 01.01.1850")[0] is None


def test_every_date_form_is_strippable_from_the_indication():
    """Captopril's indication read 'Indicated in the treatment of October-1985 h'."""
    for text in ("11.02.2025", "16.01.25", "October-1985", "16-Jan-2025"):
        assert ANY_DATE.sub("", f"Indicated for X {text} more").strip() == \
            "Indicated for X  more".replace("  ", "  ")


# ── Molecule normalisation ────────────────────────────────────────────────

def test_salts_and_dose_forms_do_not_change_the_molecule():
    assert normalise("Edoxaban Tosylate Monohydrate Bulk Drug") == "edoxaban"
    assert normalise("Fexuprazan hydrochloride Bulk Drug") == "fexuprazan"
    assert normalise("Brexpiprazole Tablets 0.25 mg") == "brexpiprazole"


def test_normalise_handles_missing_input():
    assert normalise(None) == "" and normalise("") == ""


# ── Matching ──────────────────────────────────────────────────────────────

def test_a_molecule_named_only_in_an_indication_is_not_an_approval():
    """A row whose indication mentions a comparator is not an approval of it."""
    rows = [_row("Metoprolol 50 mg + Atorvastatin 10 mg", "2009-01-01",
                 indication="compared with ramipril in hypertension")]
    assert find_approvals("Ramipril", rows)["found"] is False


def test_a_combination_counts_but_is_reported_as_a_combination():
    rows = [_row("Telmisartan 40 mg + Amlodipine 5 mg Tablets", "2009-03-31",
                 indication="For the Treatment of Essential Hypertension")]
    out = find_approvals("Telmisartan", rows)
    assert out["found"] is True
    assert out["only_as_combination"] is True
    assert out["combination_rows"] == 1 and out["single_molecule_rows"] == 0


def test_a_single_molecule_row_is_preferred_for_the_first_approval():
    rows = [_row("Ramipril + Metoprolol Tablets", "2005-01-01"),
            _row("Ramipril Capsules 5 mg", "2009-07-30",
                 indication="For the treatment of hypertension")]
    out = find_approvals("Ramipril", rows)
    assert out["only_as_combination"] is False
    assert out["first_approval_date"] == "2009-07-30"   # not the earlier combo


def test_earliest_dated_row_wins_among_single_molecule_rows():
    rows = [_row("Edoxaban Tablets 60 mg", "2025-02-20"),
            _row("Edoxaban Tablets 30 mg", "2025-02-11")]
    assert find_approvals("Edoxaban", rows)["first_approval_date"] == "2025-02-11"


def test_bulk_drug_boilerplate_is_not_kept_as_an_indication():
    rows = [_row("Tafamidis Bulk Drug", "2025-01-16",
                 indication="Not applicable as it is a bulk drug")]
    assert find_approvals("Tafamidis", rows)["india_indications"] == []


def test_provenance_travels_with_the_match():
    rows = [_row("Edoxaban Tablets 30 mg", "2025-02-11")]
    out = find_approvals("Edoxaban", rows)
    assert out["source_url"] and out["source_name"] and out["source_list"]


# ── Absence is not a negative finding ─────────────────────────────────────

def test_absence_is_never_reported_as_not_approved():
    """Tenecteplase is sold in India as Elaxim and is not in the register."""
    out = find_approvals("Tenecteplase", [_row("Edoxaban Tablets", "2025-02-11")])
    assert out["found"] is False
    assert out["approved_in_india"] is None, "must not be False"
    assert "not evidence" in out["note"]


def test_the_note_explains_why_the_register_is_incomplete():
    out = find_approvals("Inclisiran", [])
    assert "2009" in out["note"] and "scanned" in out["note"]


def test_an_empty_register_does_not_crash_or_claim_anything():
    out = find_approvals("Anything", [])
    assert out["found"] is False and out["india_indications"] == []
