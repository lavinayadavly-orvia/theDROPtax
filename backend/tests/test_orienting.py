"""
Orienting facts from openFDA.

These decide how much depth a drug warrants, so the failure that matters is a
confident wrong answer — claiming a molecule is exclusive because the lookup
came back empty, or reading US genericisation as Indian availability.

No test touches the network; the fetch is injected.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.orienting import (
    OrientingFacts, classify_exclusivity, fetch, orienting_facts, summarise,
)


ATORVASTATIN = {"results": [
    {"application_number": "NDA020702", "sponsor_name": "VIATRIS SPECIALTY",
     "submissions": [{"submission_status": "AP", "submission_status_date": "19961217"}]},
    *[{"application_number": f"ANDA07{i:04d}", "sponsor_name": f"GENERIC CO {i}",
       "submissions": [{"submission_status": "AP", "submission_status_date": "20111130"}]}
      for i in range(8)],
]}

INCLISIRAN = {"results": [
    {"application_number": "NDA214012", "sponsor_name": "NOVARTIS",
     "submissions": [{"submission_status": "AP", "submission_status_date": "20211222"}]},
]}


def _fixed(payload):
    return lambda url, timeout=25: payload


# ── Reading what is there ─────────────────────────────────────────────────

def test_genericised_molecule_is_recognised():
    f = orienting_facts("atorvastatin calcium", fetch_json=_fixed(ATORVASTATIN))
    assert f.found and f.us_has_generics is True
    assert f.us_generic_sponsors == 8
    assert f.us_exclusivity == "generic_many_makers"
    assert f.us_first_approval == "1996-12-17"
    assert f.brand_sponsor == "VIATRIS SPECIALTY"


def test_exclusive_molecule_is_recognised():
    f = orienting_facts("inclisiran", fetch_json=_fixed(INCLISIRAN))
    assert f.us_has_generics is False
    assert f.us_generic_sponsors == 0
    assert f.us_exclusivity == "exclusive"
    assert f.us_first_approval == "2021-12-22"


def test_sponsors_are_counted_not_applications():
    """One company holding six ANDAs is not a competitive market."""
    payload = {"results": [
        {"application_number": f"ANDA0{i}", "sponsor_name": "SAME CO", "submissions": []}
        for i in range(6)]}
    f = orienting_facts("x", fetch_json=_fixed(payload))
    assert f.application_count == 6
    assert f.us_generic_sponsors == 1
    assert f.us_exclusivity == "generic_few_makers"


def test_earliest_approval_wins_across_applications():
    f = orienting_facts("atorvastatin calcium", fetch_json=_fixed(ATORVASTATIN))
    assert f.us_first_approval == "1996-12-17"      # not the 2011 generics


# ── Refusing to guess ─────────────────────────────────────────────────────

def test_not_found_is_reported_as_unknown_not_as_exclusive():
    """An empty lookup must never render as 'no generics exist'."""
    f = orienting_facts("nonexistentmolecule", fetch_json=_fixed({}))
    assert f.found is False
    assert f.us_has_generics is None and f.us_exclusivity is None
    assert f.us_first_approval is None
    assert "unknown" in f.note.lower()


def test_a_network_failure_is_not_a_finding():
    def boom(url, timeout=25):
        raise OSError("connection reset")
    f = orienting_facts("atorvastatin", fetch_json=boom)
    assert f.found is False and f.us_exclusivity is None


def test_unclassifiable_exclusivity_stays_none():
    assert classify_exclusivity(None) is None


def test_malformed_dates_are_dropped_not_coerced():
    payload = {"results": [{"application_number": "NDA1", "sponsor_name": "CO",
                            "submissions": [{"submission_status": "AP",
                                             "submission_status_date": "notadate"}]}]}
    f = orienting_facts("x", fetch_json=_fixed(payload))
    assert f.found is True and f.us_first_approval is None


def test_only_approved_submissions_count():
    """A tentative or withdrawn submission is not an approval."""
    payload = {"results": [{"application_number": "NDA1", "sponsor_name": "CO",
                            "submissions": [
                                {"submission_status": "TA", "submission_status_date": "19900101"},
                                {"submission_status": "AP", "submission_status_date": "20200101"}]}]}
    f = orienting_facts("x", fetch_json=_fixed(payload))
    assert f.us_first_approval == "2020-01-01"


# ── US is not India ───────────────────────────────────────────────────────

def test_india_status_is_never_inferred_from_us_data():
    """A molecule can be genericised in India while exclusive in the US, and
    CDSCO dates differ from FDA ones by years. Nothing here may imply otherwise."""
    f = orienting_facts("inclisiran", fetch_json=_fixed(INCLISIRAN))
    d = f.to_dict()
    assert d["india_status"] is None
    assert all(k.startswith("us_") or not k.endswith(("approval", "exclusivity"))
               for k in d), "regulatory fields must be US-scoped by name"


def test_provenance_is_attached():
    f = orienting_facts("inclisiran", fetch_json=_fixed(INCLISIRAN))
    assert f.source_name and f.source_url and f.retrieved


def test_a_derived_approval_date_says_it_is_a_lower_bound():
    """For old molecules the originator application can be gone from the
    register, leaving only generics. Ramipril reads 2008 in Drugs@FDA and was
    approved in 1991 — the date must not be trusted as the first approval."""
    payload = {"results": [
        {"application_number": "ANDA076101", "sponsor_name": "GENERIC CO",
         "submissions": [{"submission_status": "AP", "submission_status_date": "20080609"}]}]}
    f = orienting_facts("ramipril", fetch_json=_fixed(payload))
    assert f.us_first_approval == "2008-06-09"
    assert f.brand_sponsor is None
    assert f.note and "lower bound" in f.note


def test_no_such_note_when_the_originator_is_present():
    f = orienting_facts("inclisiran", fetch_json=_fixed(INCLISIRAN))
    assert f.note is None
