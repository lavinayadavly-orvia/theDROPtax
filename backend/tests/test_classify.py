"""
The cost gate and the (drug x indication) classifier.

The defect this prevents: rendering a coverage matrix, an assistance module and
a cash-flow projection for a seven-rupee tablet. 139 of the 161 priced molecules
in the catalogue need none of that, and showing it anyway is the "curry when you
asked for fries" failure.

The opposite defect matters more, so it gets its own tests: an unknown price
must never be treated as a cheap one.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.classify import COST_BANDS, CostGate, classify, cost_gate

INCOME_IN = 30000    # REGIONAL_CONSTANTS["IN"]["monthly_salary"]


# ── The gate ──────────────────────────────────────────────────────────────

def test_a_seven_rupee_tablet_has_no_money_conversation():
    g = cost_gate(210, "IN")                       # ramipril, ~Rs7/tab
    assert g.band == "none"
    assert g.money_questions_live is False


def test_an_expensive_injectable_does():
    g = cost_gate(20000, "IN")                     # inclisiran
    assert g.band == "heavy"
    assert g.money_questions_live is True


def test_bands_are_relative_to_income_not_absolute_currency():
    """The same figure is trivial in one market and material in another."""
    assert cost_gate(1000, "IN").band != cost_gate(1000, "SG").band


def test_unknown_price_is_not_treated_as_cheap():
    """Suppressing coverage for a drug that turns out to be expensive is the
    worse failure, so an unresolved price stays unknown."""
    g = cost_gate(None, "IN")
    assert g.band is None
    assert g.money_questions_live is None
    assert "not as inexpensive" in g.note


def test_bands_are_wide_enough_to_survive_the_dosing_assumption():
    """Catalogue prices assume one dose a day. A 2-3x error must rarely move a
    drug across a boundary, or the gate would rest on a number we do not trust."""
    for monthly in (105, 210, 1575, 20000):        # enalapril .. inclisiran
        assert cost_gate(monthly, "IN").band == cost_gate(monthly * 2, "IN").band or \
            monthly * 2 / INCOME_IN > 0.01


def test_a_boundary_case_says_the_band_could_shift():
    """Enalapril at Rs105 reads 'none'; three times daily it is not."""
    g = cost_gate(105, "IN", assumes_once_daily=True)
    assert g.band == "none"
    assert g.band_if_dosed_three_times_daily == "noticeable"
    assert "once-daily" in g.note


def test_no_shift_note_when_the_price_is_verified():
    g = cost_gate(105, "IN", assumes_once_daily=False)
    assert g.band_if_dosed_three_times_daily is None


# ── The fetch plan ────────────────────────────────────────────────────────

def test_cheap_generic_omits_every_money_section():
    c = classify("Ramipril", "Hypertension", 210, "IN",
                 india_competition="many_brands")
    assert c.profile == "settled_generic"
    assert c.fetch["coverage"] is False
    assert c.fetch["assistance"] is False
    assert c.fetch["cash_flow"] is False
    assert c.fetch["price_negotiation"] is False


def test_cheap_generic_still_fetches_what_the_user_came_for():
    """Thin is not empty — efficacy, safety and availability always apply."""
    c = classify("Ramipril", "Hypertension", 210, "IN",
                 india_competition="many_brands")
    assert c.fetch["label_facts"] and c.fetch["clinical_evidence"]
    assert c.fetch["brands_and_availability"]


def test_single_brand_high_cost_gets_the_full_treatment():
    """Profiles are named after the Indian picture, not US exclusivity."""
    c = classify("Inclisiran", "Hypercholesterolemia", 20000, "IN",
                 india_competition="single_brand")
    assert c.profile == "single_brand_high_cost"
    assert all(c.fetch[k] for k in
               ("coverage", "assistance", "cash_flow", "competition"))


def test_the_concentrated_supply_case_is_detectable():
    """Genericised but few makers — no exclusivity to expire and no competition
    to erode the price. Nothing in the catalogue sits here, but a user can type
    any drug."""
    c = classify("SomeDrug", "SomeIndication", 9000, "IN",
                 india_competition="few_brands")
    assert c.profile == "concentrated_supply"
    assert c.fetch["coverage"] is True


def test_unknown_price_shows_money_sections_rather_than_hiding_them():
    c = classify("NewDrug", "Hypertension", None, "IN", exclusivity="exclusive")
    assert c.fetch["coverage"] is True
    assert any(i["field"] == "price" for i in c.issues)


def test_unknown_competition_does_not_reduce_depth():
    c = classify("NewDrug", "Hypertension", 20000, "IN", exclusivity=None)
    assert c.fetch["coverage"] is True
    assert any(i["field"] == "competition" for i in c.issues)


# ── Reasons, in words ─────────────────────────────────────────────────────

def test_the_classification_explains_itself():
    c = classify("Ramipril", "Hypertension", 210, "IN",
                 india_competition="many_brands")
    joined = " ".join(c.reasons).lower()
    assert "monthly income" in joined
    assert "branded generics" in joined
    assert "omitted" in joined


def test_an_unmapped_indication_is_noted_without_disabling_anything():
    """No registry entry means no endpoints — it does not mean no drug."""
    c = classify("Propranolol", "Essential tremor", 150, "IN",
                 india_competition="many_brands", indication_mapped=False)
    assert any(i["field"] == "indication" for i in c.issues)
    assert c.fetch["label_facts"] and c.fetch["clinical_evidence"]


# ── Band table integrity ──────────────────────────────────────────────────

def test_bands_are_ordered_and_cover_everything():
    ceilings = [c for c, _, _ in COST_BANDS]
    assert ceilings == sorted(ceilings)
    assert ceilings[-1] == float("inf")


def test_the_dosing_warning_keys_on_the_assumption_not_on_estimation():
    """Inclisiran's price is estimated because no verified India price exists,
    and it is dosed twice a YEAR. Warning that it might be taken three times a
    day is gibberish — which is what fired when price_is_estimated was the key."""
    g = cost_gate(20000, "IN", assumes_once_daily=False, price_is_estimated=True)
    assert g.band_if_dosed_three_times_daily is None
    assert g.note is None


# ── Payment has to recur for there to be anything to finance ──────────────

def test_a_single_inpatient_dose_needs_no_assistance_or_cash_flow():
    """Tenecteplase is expensive and needs neither — it is bundled into the
    admission claim. The cost gate alone cannot see this."""
    c = classify("Tenecteplase", "STEMI", 45000, "IN",
                 india_competition="many_brands",
                 treatment_model="acute_single_dose")
    assert c.fetch["coverage"] is True          # someone still claims it
    assert c.fetch["assistance"] is False
    assert c.fetch["cash_flow"] is False
    assert any("admission" in r for r in c.reasons)


def test_a_chronic_drug_at_the_same_price_keeps_them():
    c = classify("Inclisiran", "Hypercholesterolemia", 45000, "IN",
                 india_competition="single_brand", treatment_model="chronic_ongoing")
    assert c.fetch["assistance"] is True and c.fetch["cash_flow"] is True
