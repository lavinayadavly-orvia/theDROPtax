"""
Dynamic Evidence Appraisal Engine — PRD v1.3.0 §4.3 / §5.1.

The three calibration cases from the PRD are the acceptance tests. If a weight
profile is changed and one of these flips, the change is wrong or the PRD needs
updating — either way it should fail loudly here first.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.appraisal import (
    Study, Intent, Region, WEIGHT_PROFILES, appraise, rank,
    normalise_exposure, proximity_for, detect_divergence,
)


# ── Profile integrity ─────────────────────────────────────────────────────

def test_every_weight_profile_sums_to_one():
    for intent, w in WEIGHT_PROFILES.items():
        assert abs(sum(w.values()) - 1.0) < 1e-9, f"{intent} weights do not sum to 1"


def test_no_fixed_hierarchy_between_profiles():
    """The point of the engine: the same dimension is weighted differently."""
    assert WEIGHT_PROFILES[Intent.SAFETY]["size"] > WEIGHT_PROFILES[Intent.EFFICACY]["size"]
    assert WEIGHT_PROFILES[Intent.EFFICACY]["shape"] > WEIGHT_PROFILES[Intent.SAFETY]["shape"]
    assert WEIGHT_PROFILES[Intent.ACCESS]["relevance"] > WEIGHT_PROFILES[Intent.EFFICACY]["relevance"]


# ── Calibration Case 1 — Safety (PRD §4.3.1) ──────────────────────────────
# "A 5-year PSM EMR registry (N=45,000, 225k patient-years) outranks an
#  18-month Phase III RCT (N=1,561) for identifying long-term or rare safety
#  signals."

PIVOTAL_RCT = Study(
    study_id="ORION-10", title="Phase III placebo-controlled RCT",
    shape=9.5, exposure_years=1561 * 1.5, endpoint=6.0, rigor=9.0,
    cohort="western", design="RCT", n=1561, followup_years=1.5,
)
PSM_REGISTRY = Study(
    study_id="RWE-EMR-5Y", title="5-year propensity-matched EMR registry",
    shape=6.0, exposure_years=45000 * 5, endpoint=6.0, rigor=7.0,
    cohort="western", design="PSM observational", n=45000, followup_years=5.0,
)


def test_case1_registry_outranks_rct_on_safety():
    out = rank([PIVOTAL_RCT, PSM_REGISTRY], Intent.SAFETY, Region.INDIA)
    assert out["ranked"][0].study_id == "RWE-EMR-5Y", (
        "PRD §4.3.1: the long-exposure registry must lead a safety query")


def test_case1_flips_back_under_efficacy():
    """Same two papers, different question, different leader."""
    out = rank([PIVOTAL_RCT, PSM_REGISTRY], Intent.EFFICACY, Region.INDIA)
    ids = [r.study_id for r in out["ranked"]]
    assert ids.index("ORION-10") < ids.index("RWE-EMR-5Y") or \
        out["ranked"][0].score == out["ranked"][1].score, (
        "Design weighting should favour the RCT once the question is efficacy")


# ── Calibration Case 2 — Regional Access (PRD §4.3.3) ─────────────────────
# "An Indian multi-center PSM cohort (N=3,500) outranks a massive Western RCT
#  (N=17,000) under the India toggle."

WESTERN_RCT = Study(
    study_id="GLOBAL-CVOT", title="Global pivotal RCT, Western cohort",
    shape=9.5, exposure_years=17000 * 3.0, endpoint=9.5, rigor=9.5,
    cohort="western", design="RCT", n=17000, followup_years=3.0,
)
INDIAN_PSM = Study(
    study_id="IN-PSM-2025", title="Indian multi-centre propensity-matched cohort",
    shape=7.5, exposure_years=3500 * 2.0, endpoint=8.0, rigor=8.0,
    cohort="south_asian", design="PSM observational", n=3500, followup_years=2.0,
)


def test_case2_indian_cohort_leads_under_india_access():
    out = rank([WESTERN_RCT, INDIAN_PSM], Intent.ACCESS, Region.INDIA)
    assert out["ranked"][0].study_id == "IN-PSM-2025", (
        "PRD §4.3.3: population fit must dominate a regional access query")


def test_case2_western_rct_leads_on_efficacy():
    """The same Western trial should lead when the question is efficacy."""
    out = rank([WESTERN_RCT, INDIAN_PSM], Intent.EFFICACY, Region.INDIA)
    assert out["ranked"][0].study_id == "GLOBAL-CVOT"


# ── Calibration Case 3 — Efficacy (PRD §4.3.2) ────────────────────────────
# "A post-marketing CVOT showing hard MACE reduction outranks a Phase II/III
#  trial evaluating surrogate biomarkers."

BIOMARKER_TRIAL = Study(
    study_id="PH2-LDL", title="Phase II/III surrogate-endpoint trial",
    shape=9.0, exposure_years=800 * 0.46, endpoint=6.0, rigor=9.0,
    cohort="western", design="RCT", n=800, followup_years=0.46,
)
HARD_OUTCOME_CVOT = Study(
    study_id="CVOT-MACE", title="Cardiovascular outcomes trial, hard MACE endpoint",
    shape=9.5, exposure_years=12000 * 3.5, endpoint=10.0, rigor=9.5,
    cohort="western", design="RCT", n=12000, followup_years=3.5,
)


def test_case3_hard_endpoint_outranks_surrogate():
    out = rank([BIOMARKER_TRIAL, HARD_OUTCOME_CVOT], Intent.EFFICACY, Region.INDIA)
    assert out["ranked"][0].study_id == "CVOT-MACE", (
        "PRD §4.3.2: a hard clinical endpoint must outrank a surrogate biomarker")


# ── §5.1 Ethno-geographic proximity ───────────────────────────────────────

@pytest.mark.parametrize("region,cohort,expected", [
    (Region.INDIA, "south_asian", 1.00),
    (Region.INDIA, "south_asian_diaspora", 0.75),
    (Region.INDIA, "east_asian", 0.45),
    (Region.INDIA, "western", 0.20),
    (Region.SINGAPORE, "singaporean", 1.00),
    (Region.SINGAPORE, "east_asian", 0.75),
    (Region.SINGAPORE, "se_asian", 0.45),
    (Region.UAE, "gcc_arab", 1.00),
    (Region.UAE, "mena", 0.75),
    (Region.UAE, "south_asian_expat", 0.75),
])
def test_proximity_matrix(region, cohort, expected):
    value, _ = proximity_for(region, cohort)
    assert value == expected


def test_unknown_cohort_falls_to_tier3_never_better():
    """An unrecognised cohort must not be given the benefit of the doubt."""
    value, tier = proximity_for(Region.INDIA, "unspecified population")
    assert value == 0.20 and "Tier 3" in tier


def test_east_asian_is_moderate_proxy_for_india_not_global():
    """PRD §5.1 operational rule: East Asian scores 0.45 for India — better
    than Western (0.20), well below South Asian (1.0)."""
    ea, _ = proximity_for(Region.INDIA, "east_asian")
    we, _ = proximity_for(Region.INDIA, "western")
    sa, _ = proximity_for(Region.INDIA, "south_asian")
    assert we < ea < sa


# ── §5.2 Warning badges ───────────────────────────────────────────────────

def test_tier1_carries_no_warning_badge():
    a = appraise(INDIAN_PSM, Intent.ACCESS, Region.INDIA)
    assert a.warning_badge is None


def test_tier3_renders_global_fallback_badge():
    a = appraise(WESTERN_RCT, Intent.ACCESS, Region.INDIA)
    assert a.warning_badge and "Global Evidence Fallback" in a.warning_badge


def test_tier2_renders_proxy_badge():
    diaspora = Study(study_id="UKB-SA", title="UK Biobank South Asian subgroup",
                     shape=7.0, exposure_years=5000 * 4, endpoint=8.0, rigor=8.0,
                     cohort="south_asian_diaspora", n=5000)
    a = appraise(diaspora, Intent.ACCESS, Region.INDIA)
    assert a.warning_badge and "Regional Proxy Data" in a.warning_badge


# ── Presentation contract: rank, never filter ─────────────────────────────

def test_nothing_is_filtered_out():
    out = rank([PIVOTAL_RCT, PSM_REGISTRY, WESTERN_RCT, INDIAN_PSM],
               Intent.SAFETY, Region.INDIA)
    assert len(out["ranked"]) + len(out["unscored"]) == out["total_considered"] == 4


def test_active_weights_are_returned_for_display():
    """The user must be able to see what drove the order."""
    out = rank([PIVOTAL_RCT], Intent.SAFETY, Region.INDIA)
    assert out["active_weights"] == WEIGHT_PROFILES[Intent.SAFETY]
    assert out["ranked"][0].contributions          # per-dimension breakdown


def test_missing_component_yields_unscored_not_zero():
    """A gap in extraction must not be scored as a weakness in the study."""
    partial = Study(study_id="X", title="Endpoint not extracted",
                    shape=9.0, exposure_years=1000, endpoint=None,
                    rigor=8.0, cohort="south_asian")
    a = appraise(partial, Intent.EFFICACY, Region.INDIA)
    assert a.score is None and "endpoint" in a.unscorable_reason


# ── Exposure normalisation ────────────────────────────────────────────────

def test_exposure_is_log_scaled_and_capped():
    assert normalise_exposure(100_000) == pytest.approx(10.0, abs=0.01)
    assert normalise_exposure(225_000) == 10.0            # capped
    assert normalise_exposure(None) is None
    assert normalise_exposure(0) is None
    assert normalise_exposure(2341) < normalise_exposure(225_000)


# ── §4.2 Divergence ───────────────────────────────────────────────────────

def test_divergence_surfaces_label_vs_real_world_gap():
    msg = detect_divergence(52.0, 41.0, "LDL-C reduction")
    assert msg and "52" in msg and "41" in msg
    assert "neither supersedes" in msg


def test_no_divergence_claimed_when_a_side_is_unknown():
    assert detect_divergence(52.0, None, "LDL-C reduction") is None
    assert detect_divergence(None, 41.0, "LDL-C reduction") is None


def test_small_differences_are_not_flagged_as_divergence():
    assert detect_divergence(52.0, 50.0, "LDL-C reduction") is None


# ── Partial appraisal ─────────────────────────────────────────────────────
# Real abstracts routinely omit follow-up duration or carry no design label.
# Refusing to rank anything incomplete left 23 of 25 live papers unranked, so a
# study is scored on the dimensions it did report — with the basis declared.

def _partial(**overrides):
    base = dict(study_id="P", title="Partially extracted paper", shape=9.0,
                exposure_years=5000.0, endpoint=8.0, rigor=7.0, cohort="south_asian")
    base.update(overrides)
    return Study(**base)


def test_missing_dimension_is_excluded_from_the_arithmetic_not_imputed():
    """The renormalised score must equal the mean over PRESENT dimensions."""
    a = appraise(_partial(exposure_years=None), Intent.EFFICACY, Region.INDIA)
    assert a.score is None                       # strict contract unchanged
    assert a.partial_score is not None
    assert "size" in a.missing and "size" not in a.scored_on
    w = WEIGHT_PROFILES[Intent.EFFICACY]
    mass = sum(w[k] for k in a.scored_on)
    expected = sum(w[k] / mass * a.components[k] for k in a.scored_on)
    assert a.partial_score == pytest.approx(expected, abs=0.01)


def test_partial_score_declares_what_it_rests_on():
    a = appraise(_partial(rigor=None), Intent.SAFETY, Region.INDIA)
    assert "partial" in a.basis_note and "rigor" in a.basis_note
    assert 0 < a.weight_mass < 1.0


def test_too_little_weight_mass_yields_no_score_at_all():
    """A paper known only by its endpoint is not thereby a strong paper."""
    a = appraise(_partial(shape=None, exposure_years=None, rigor=None,
                          cohort=None), Intent.EFFICACY, Region.INDIA)
    # endpoint (0.35) + relevance (0.05, always present) = 0.40 < MIN_WEIGHT_MASS
    assert a.partial_score is None and a.effective_score is None
    assert "not scored" in a.basis_note


def test_partial_and_full_scores_share_one_ordering():
    """Splitting them would bury a strong paper that omitted its follow-up."""
    full = _partial(study_id="FULL", shape=5.0, endpoint=5.0, rigor=5.0)
    thin = _partial(study_id="THIN", exposure_years=None, shape=9.5,
                    endpoint=10.0, rigor=9.5)
    out = rank([full, thin], Intent.EFFICACY, Region.INDIA)
    assert out["ranked"][0].study_id == "THIN"
    assert out["fully_scored"] == 1 and out["partially_scored"] == 1


def test_counts_still_account_for_every_study():
    out = rank([_partial(), _partial(study_id="Q", shape=None, exposure_years=None,
                                     rigor=None, cohort=None, endpoint=None)],
               Intent.EFFICACY, Region.INDIA)
    assert len(out["ranked"]) + len(out["unscored"]) == out["total_considered"] == 2
