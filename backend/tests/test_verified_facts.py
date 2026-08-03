"""
Source-verified facts must carry a citation and must not be written from memory.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.verified_facts import (
    VERIFIED_FACTS, get_verified, verified_value, doses_per_year, verification_summary,
)


def test_every_verified_fact_cites_a_source_and_a_date():
    """A fact without provenance is indistinguishable from a guess."""
    for molecule, rec in VERIFIED_FACTS.items():
        for key, fact in rec.get("facts", {}).items():
            assert fact.get("source_name"), f"{molecule}.{key} has no source_name"
            assert fact.get("source_url", "").startswith("http"), f"{molecule}.{key} has no source_url"
            assert re.match(r"^\d{4}-\d{2}-\d{2}$", fact.get("retrieved", "")), \
                f"{molecule}.{key} has no ISO retrieval date"


def test_inclisiran_matches_the_fda_label_not_the_workbook():
    """The workbook said "FDA Jan 2024" and "twice-yearly"; the label says otherwise."""
    year, prov = verified_value("inclisiran", "us_initial_approval_year")
    assert year == 2021
    assert "dailymed" in prov["source_url"]

    y1, maint = doses_per_year("inclisiran")
    assert (y1, maint) == (3, 2), "Loading-dose regimen must be 3 doses in year 1, then 2"


def test_loading_dose_quote_is_preserved_verbatim():
    """Where wording carries the meaning, the quote must be retained."""
    sched = VERIFIED_FACTS["inclisiran"]["facts"]["dosing_schedule"]
    assert "again at 3 months" in sched["quote"]
    assert "every 6 months" in sched["quote"]


def test_unverified_fields_are_declared_rather_than_assumed():
    """No Indian price/brand source has been read, so those stay outstanding."""
    rec = get_verified("inclisiran")
    outstanding = rec["not_yet_verified"]
    assert "india_price_per_dose" in outstanding
    assert "india_brands" in outstanding
    # And they must NOT appear as verified facts.
    assert not (set(outstanding) & set(rec["facts"].keys()))


def test_verification_summary_reports_sources():
    summary = verification_summary()
    assert summary["molecules_verified"] >= 1
    incl = summary["molecules"]["inclisiran"]
    assert incl["sources"] and all(u.startswith("http") for u in incl["sources"])
