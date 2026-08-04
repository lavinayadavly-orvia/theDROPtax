"""
Structuring indication prose into (drug x indication) units.

112 of 218 catalogue rows named several indications inside one string, so the
platform treated every molecule as having exactly one use. These tests pin the
splitting rules — which were read off the data, not assumed — and the guard
against confidently mis-routing an indication to the wrong therapy area.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.indications import parse, structure
from core.therapy_areas import resolve_indication


# ── Splitting ─────────────────────────────────────────────────────────────

def test_semicolon_is_the_separator():
    out = parse("Hypertension; heart failure; post-MI")
    assert [i.text for i in out] == ["Hypertension", "Heart failure", "Post-MI"]


def test_commas_never_split():
    """No catalogue row uses a comma as its only separator, and several carry
    commas inside parentheses. Splitting on them would invent indications."""
    out = parse("Osteoporosis (Prolia, 6-monthly)")
    assert len(out) == 1
    assert out[0].text == "Osteoporosis"
    assert "6-monthly" in out[0].qualifier


def test_parenthetical_is_a_qualifier_not_an_indication():
    out = parse("high CV-risk (HOPE, EUROPA trials)")
    assert len(out) == 1
    assert out[0].qualifier == "HOPE, EUROPA trials"


def test_also_inside_parentheses_names_a_further_indication():
    out = parse("Pulmonary arterial hypertension (also erectile dysfunction)")
    assert [i.text for i in out] == ["Pulmonary arterial hypertension",
                                     "Erectile dysfunction"]


def test_off_label_is_flagged_and_stripped_from_the_name():
    out = parse("Hypertension; off-label tocolysis")
    tocolysis = out[-1]
    assert tocolysis.off_label is True
    assert "off-label" not in tocolysis.text.lower()
    assert tocolysis.text == "Tocolysis"


def test_acronyms_keep_their_case():
    out = parse("HFrEF; DUB; PPH")
    assert [i.text for i in out] == ["HFrEF", "DUB", "PPH"]


def test_empty_input_yields_no_placeholder_indication():
    """A drug with no recorded indication is a gap, not an indication called
    'unknown'."""
    assert parse("") == [] and parse(None) == []
    s = structure(None)
    assert s["indication_count"] == 0 and s["primary_indication"] is None


# ── Mapping, and refusing to mis-map ──────────────────────────────────────

def test_portal_hypertension_does_not_resolve_to_systemic_hypertension():
    """The alias 'htn' sits inside 'portal HTN'. Substring matching routed it to
    Hypertension, which would apply blood-pressure endpoints to variceal bleed
    prophylaxis. Unmapped is recoverable; confidently wrong is not."""
    assert resolve_indication("Portal HTN") is None
    assert resolve_indication("portal hypertension") is None


@pytest.mark.parametrize("text", ["intracranial hypertension", "ocular hypertension"])
def test_other_anatomical_hypertensions_are_refused_too(text):
    assert resolve_indication(text) is None


def test_the_guard_does_not_break_a_registry_entry_that_exists():
    """Pulmonary arterial hypertension is in the registry, so the alias lookup
    returns it before the modifier guard is ever reached."""
    for text in ("Pulmonary arterial hypertension", "PAH"):
        entry = resolve_indication(text)
        assert entry and entry["indication"] == "Pulmonary Arterial Hypertension"


def test_ordinary_hypertension_still_resolves():
    for text in ("Hypertension", "resistant hypertension", "htn"):
        entry = resolve_indication(text)
        assert entry and entry["indication"] == "Hypertension"


def test_alias_must_match_on_a_word_boundary():
    """A short alias must not match inside an unrelated word."""
    assert resolve_indication("xhtnx") is None


def test_unmapped_indications_are_kept_not_dropped():
    """Dropping them would quietly shrink the drug's real scope."""
    s = structure("Hypertension; Raynaud; essential tremor")
    assert s["indication_count"] == 3
    assert "Raynaud" in s["unmapped"] and "Essential tremor" in s["unmapped"]


# ── The structured record ─────────────────────────────────────────────────

def test_primary_is_the_first_that_reaches_the_registry():
    """That is the indication bringing the drug into scope."""
    s = structure("Migraine prophylaxis; hypertension")
    assert s["primary_indication"] == "Hypertension"
    assert s["primary_registry_indication"] == "Hypertension"


def test_primary_falls_back_without_claiming_a_therapy_area():
    s = structure("Raynaud; essential tremor")
    assert s["primary_indication"] == "Raynaud"
    assert s["primary_registry_indication"] is None
    assert s["primary_category"] is None


def test_multi_indication_flag_reflects_the_text():
    assert structure("Hypercholesterolemia")["has_multiple_indications"] is False
    assert structure("Hypertension; angina")["has_multiple_indications"] is True


def test_a_seven_indication_row_survives_intact():
    s = structure("Hypertension; angina; arrhythmia; migraine prophylaxis; "
                  "essential tremor; thyrotoxicosis; portal HTN (variceal bleed prophylaxis)")
    assert s["indication_count"] == 7
    portal = s["indications"][-1]
    assert portal["text"] == "Portal HTN" and portal["mapped"] is False
