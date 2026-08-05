"""
The Indian competitive picture, and where the US picture would mislead.

Drugs@FDA called tenecteplase exclusive to Genentech with zero generic
sponsors, so the classifier printed "No generic competition — the originator
sets the price." The same catalogue row holds brands Elaxim and Tenectase from
Emcure. That statement was false for the market this platform serves, and
these tests exist to keep it false-proof.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.classify import classify
from core.india_market import (
    classify_competition, india_market, parse_list, reconcile_with_us,
)


# ── Parsing free-text brand and maker lists ───────────────────────────────

def test_named_entries_are_separated_from_vague_ones():
    """'Emcure, generics' names one company AND asserts there are more.
    Both facts matter; dropping either loses information."""
    out = parse_list("Emcure, generics")
    assert out["named"] == ["Emcure"]
    assert out["implies_more"] is True


def test_joint_ventures_split_on_a_slash():
    assert parse_list("Serdia/Servier")["named"] == ["Serdia", "Servier"]


def test_empty_input_asserts_nothing():
    for text in (None, "", "   "):
        out = parse_list(text)
        assert out["named"] == [] and out["implies_more"] is False


# ── The competition signal ────────────────────────────────────────────────

def test_no_data_is_unknown_not_uncontested():
    m = india_market({"key_brands": None, "manufacturers": None})
    assert m["competition"] is None
    assert "not evidence" in m["note"]


def test_a_vague_maker_entry_implies_wider_competition():
    m = india_market({"key_brands": "Elaxim, Tenectase", "manufacturers": "Emcure, generics"})
    assert m["competition"] == "many_brands"
    assert m["more_makers_implied"] is True


def test_counts_are_declared_as_lower_bounds():
    """key_brands lists brands worth knowing, not every brand. Ramipril carries
    three here and far more in reality."""
    m = india_market({"key_brands": "Cardace, Ramistar, Hopace",
                      "manufacturers": "Sanofi, Lupin, USV"})
    assert m["brand_count_floor"] == 3
    assert m["counts_are_lower_bounds"] is True
    assert "floor" in m["note"] or m["competition"] == "few_brands"


def test_a_single_brand_says_the_count_is_a_floor():
    m = india_market({"key_brands": "Leqvio", "manufacturers": "Novartis"})
    assert m["competition"] == "single_brand"
    assert "floor" in m["note"]


@pytest.mark.parametrize("brands,makers,more,expected", [
    (0, 0, False, None),
    (1, 1, False, "single_brand"),
    (3, 3, False, "few_brands"),
    (6, 2, False, "many_brands"),
    (2, 1, True, "many_brands"),
])
def test_competition_states(brands, makers, more, expected):
    assert classify_competition(brands, makers, more) == expected


# ── Reconciling with the US reading ───────────────────────────────────────

def test_us_exclusivity_against_indian_brands_raises_a_conflict():
    """The tenecteplase case."""
    m = india_market({"key_brands": "Elaxim, Tenectase", "manufacturers": "Emcure"})
    warning = reconcile_with_us(m, "exclusive")
    assert warning and "Emcure" in warning
    assert "does not describe this market" in warning


def test_no_conflict_when_both_agree():
    m = india_market({"key_brands": "Leqvio", "manufacturers": "Novartis"})
    assert reconcile_with_us(m, "exclusive") is None


def test_no_conflict_claimed_when_india_is_unknown():
    m = india_market({"key_brands": None, "manufacturers": None})
    assert reconcile_with_us(m, "exclusive") is None


# ── The classifier must not report the US position as India's ─────────────

def test_india_competition_overrides_the_us_reading():
    c = classify("Tenecteplase", "STEMI", 45000, "IN",
                 exclusivity="exclusive", india_competition="many_brands")
    joined = " ".join(c.reasons).lower()
    assert "no generic competition" not in joined
    assert "branded generics" in joined


def test_the_conflict_is_surfaced_as_an_issue():
    c = classify("Tenecteplase", "STEMI", 45000, "IN",
                 exclusivity="exclusive", india_competition="many_brands",
                 india_us_conflict="US records show no generic competition, but "
                                   "this molecule is marketed in India by Emcure.")
    assert any(i["field"] == "competition" and i["severity"] == "warning"
               for i in c.issues)


def test_the_us_signal_is_labelled_as_pipeline_only_when_used_alone():
    c = classify("NewDrug", "Hypertension", 20000, "IN",
                 exclusivity="exclusive", india_competition=None)
    joined = " ".join(c.reasons).lower()
    assert "pipeline signal" in joined
    assert "does not describe this market" in joined


# ── CDSCO permissions ─────────────────────────────────────────────────────

def _perm(firm, kind="manufacture", date=None):
    return {"firm": firm, "permission_type": kind, "permission_date": date}


def test_manufacture_permissions_are_the_competition_signal():
    """A molecule several Indian firms may manufacture is contested here,
    whatever its patent status is anywhere else."""
    perms = [_perm(f"M/s Firm {i}", date="2023-01-01") for i in range(6)]
    m = india_market({"key_brands": None, "manufacturers": None}, perms)
    assert m["competition"] == "many_brands"
    assert m["evidence"] == "CDSCO permissions"
    assert m["cdsco"]["manufacture_count"] == 6


def test_import_permissions_describe_entry_not_competition():
    """An importer is how the molecule arrived, not who competes with it."""
    perms = [_perm("M/s Novartis", kind="import", date="2023-07-06")]
    m = india_market({"key_brands": None, "manufacturers": None}, perms)
    assert m["cdsco"]["import_count"] == 1
    assert m["cdsco"]["manufacture_count"] == 0
    assert m["evidence"] == "catalogue key brands"   # imports do not set the state


def test_cdsco_is_better_evidence_but_not_more_complete():
    """The consolidated r-DNA file lists one manufacturer for tenecteplase; a
    monthly file names another and the catalogue a third. Letting CDSCO
    override turned a contested molecule into a single-brand one."""
    perms = [_perm("M/s Gennova Biopharmaceuticals", date="2023-10-27")]
    drug = {"key_brands": "Elaxim, Tenectase", "manufacturers": "Emcure, generics"}
    m = india_market(drug, perms)
    assert m["competition"] == "many_brands", "the 'generics' signal must survive"
    assert m["more_makers_implied"] is True


def test_the_higher_floor_wins_across_sources():
    perms = [_perm("M/s One", date="2023-01-01")]
    drug = {"key_brands": "A, B, C", "manufacturers": "X, Y, Z"}
    assert india_market(drug, perms)["competition"] == "few_brands"


def test_no_permissions_leaves_the_catalogue_in_charge():
    m = india_market({"key_brands": "Cardace", "manufacturers": "Sanofi"}, [])
    assert m["cdsco"] is None and m["evidence"] == "catalogue key brands"


def test_the_unknown_note_names_both_registers_gaps():
    """Absence must not read as uncontested: the r-DNA register covers
    biologicals only, and the new-drug lists miss import permissions."""
    m = india_market({"key_brands": None, "manufacturers": None}, [])
    assert m["competition"] is None
    assert "biologicals only" in m["note"] and "import permission" in m["note"]
