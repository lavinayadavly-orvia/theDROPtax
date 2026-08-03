"""
Therapy Area Registry tests — the single source of truth for endpoints.

These are pure unit tests (no live API, no DB) so they run anywhere.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.therapy_areas import (
    INDICATION_REGISTRY,
    resolve_indication,
    get_category,
    normalize_efficacy,
    event_probability_from_primary,
    build_endpoints_summary,
)


# ── Registry integrity ────────────────────────────────────────────────────

def test_registry_has_no_oncology_endpoints():
    """The whole point of the migration: no oncology endpoints anywhere.

    Acronyms are matched on word boundaries — 'ORR' must not false-positive on
    legitimate gynaecology terms such as Menorrhagia / Dysmenorrhoea.
    """
    import re
    # NB: "TIMI grade 3 flow" is legitimate cardiology nomenclature, so CTCAE
    # grading is matched specifically (grade 3/4 adverse events), not "grade 3".
    banned_phrases = ["progression-free", "overall survival", "objective response",
                      "disease control", "duration of response", "tumor", "tumour",
                      "recist", "chemo", "oncolog", "carcinoma", "metasta"]
    banned_patterns = [r"grade\s*3\s*/\s*4", r"grade\s*3\s+adverse", r"grade\s*4\s+adverse"]
    banned_acronyms = ["pfs", "orr", "dcr", "dor", "os", "ctcae"]
    blob = repr(INDICATION_REGISTRY).lower()

    for term in banned_phrases:
        assert term not in blob, f"Oncology term '{term}' still present in the registry"
    for pat in banned_patterns:
        assert not re.search(pat, blob), f"Oncology grading pattern '{pat}' still present in the registry"
    for acro in banned_acronyms:
        assert not re.search(rf"\b{acro}\b", blob), f"Oncology acronym '{acro}' still present in the registry"


def test_every_entry_is_well_formed():
    for key, entry in INDICATION_REGISTRY.items():
        assert entry["category"] in {"CVD", "CVS", "Metabolic", "Women's Health"}
        pe = entry["primary_endpoint"]
        for field in ("key", "label", "unit", "direction", "norm"):
            assert field in pe, f"{key} primary_endpoint missing {field}"
        assert pe["direction"] in {"higher_better", "lower_better"}
        assert pe["norm"]["type"] in {"months", "reduction_pct", "rate_pct", "hr", "mmhg", "inverse_rate"}
        assert entry["treatment_model"] in {"acute_single_dose", "fixed_course", "chronic_ongoing"}
        assert entry["route_default"] in {"iv_bolus", "iv_infusion", "sc_injection", "oral"}


# ── Indication resolution ─────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected_category", [
    ("Heart Failure", "CVD"),
    ("Cardiovascular Risk Reduction", "CVD"),
    ("Hypercholesterolemia", "CVD"),
    ("Dyslipidemia", "CVD"),                      # alias
    ("Hypertension", "CVD"),
    ("Acute Ischemic Stroke", "CVS"),
    ("Acute Myocardial Infarction", "CVS"),
    ("Chronic Weight Management", "Metabolic"),
    ("Obesity", "Metabolic"),                     # alias
    ("Type 2 Diabetes", "Metabolic"),
    ("Vasomotor Symptoms", "Women's Health"),
    ("Menopause", "Women's Health"),              # alias
    ("Osteoporosis", "Women's Health"),
    ("Endometriosis", "Women's Health"),
    ("Uterine Fibroids", "Women's Health"),
    ("Heavy Menstrual Bleeding", "Women's Health"),
    ("Menorrhagia", "Women's Health"),            # alias
    # Cardiology additions
    ("Chronic stable angina", "CVD"),
    ("Ventricular arrhythmias; AF", "CVD"),
    ("Non-valvular AF; VTE", "CVD"),
    # Obstetrics additions
    ("PPH; uterine atony", "Women's Health"),
    ("Threatened preterm labor", "Women's Health"),
    ("Cervical ripening & induction of labor", "Women's Health"),
    ("Iron-deficiency anemia in pregnancy", "Women's Health"),
    ("Eclampsia/severe pre-eclampsia seizure prophylaxis", "Women's Health"),
    ("Fetal lung maturation in threatened preterm birth", "Women's Health"),
    ("Menopausal symptoms; atrophic vaginitis", "Women's Health"),   # HRT -> VMS
])
def test_resolve_indication_and_category(text, expected_category):
    entry = resolve_indication(text)
    assert entry is not None, f"{text} should resolve"
    assert entry["category"] == expected_category
    assert get_category(text) == expected_category


def test_unknown_indication_resolves_to_none():
    """Anti-hallucination: unknown indications must not be silently mis-routed."""
    assert resolve_indication("Some Unlisted Condition XYZ") is None
    assert resolve_indication(None) is None
    assert resolve_indication("") is None


def test_obesity_and_weight_management_are_the_same_entry():
    assert resolve_indication("Obesity") is resolve_indication("Chronic Weight Management")


# ── Endpoint normalisation & the value driver ─────────────────────────────

def test_hazard_ratio_normalisation_is_inverted():
    """HR is lower-better: a stronger HR must give higher efficacy."""
    hf = resolve_indication("Heart Failure")
    strong = normalize_efficacy(hf["primary_endpoint"]["norm"], 0.75)  # 25% RRR
    weak = normalize_efficacy(hf["primary_endpoint"]["norm"], 0.95)    # 5% RRR
    assert strong > weak


def test_event_probability_moves_inversely_with_efficacy():
    hf = resolve_indication("Heart Failure")
    good = event_probability_from_primary(hf, 0.75)
    poor = event_probability_from_primary(hf, 0.95)
    assert good < poor
    assert 0.0 <= good <= 1.0 and 0.0 <= poor <= 1.0


def test_rate_endpoint_normalisation_is_direct():
    """Functional independence is higher-better."""
    stroke = resolve_indication("Acute Ischemic Stroke")
    assert event_probability_from_primary(stroke, 65.0) < event_probability_from_primary(stroke, 20.0)


def test_missing_primary_value_yields_none_not_a_default():
    """Anti-hallucination: no value → no fabricated probability."""
    hf = resolve_indication("Heart Failure")
    assert event_probability_from_primary(hf, None) is None
    assert normalize_efficacy(hf["primary_endpoint"]["norm"], None) is None


# ── Endpoints summary rendering ───────────────────────────────────────────

def test_endpoints_summary_marks_unavailable_values():
    entry = resolve_indication("Type 2 Diabetes")
    rows = build_endpoints_summary(entry, None, {})
    primary = rows[0]
    assert primary["is_primary"] is True
    assert primary["available"] is False
    assert primary["value"] == "Data unavailable"


def test_endpoints_summary_renders_available_values():
    entry = resolve_indication("Chronic Weight Management")
    rows = build_endpoints_summary(entry, 20.9, {"responder_10": 83.0})
    assert rows[0]["available"] is True
    assert "20.9" in rows[0]["value"]
    responder = next(r for r in rows if r["key"] == "responder_10")
    assert responder["available"] is True


# ── Anticoagulant vs antiarrhythmic disambiguation ────────────────────────

def test_anticoagulants_and_antiarrhythmics_do_not_collide():
    """Both mention atrial fibrillation but need different primary endpoints."""
    apixaban = resolve_indication("Non-valvular AF; VTE treatment/prevention")
    amiodarone = resolve_indication("VT/VF; AF/atrial flutter; life-threatening arrhythmias")
    assert apixaban["primary_endpoint"]["key"] == "stroke_se_hr"
    assert amiodarone["primary_endpoint"]["key"] == "sinus_rhythm"
    assert apixaban["safety_label"] == "Major bleeding"


def test_obstetric_acute_drugs_are_inpatient_single_dose():
    """Uterotonics and induction agents are given at delivery, in hospital."""
    for text in ("PPH; uterine atony", "Induction/augmentation of labor"):
        e = resolve_indication(text)
        assert e["treatment_model"] == "acute_single_dose"
        assert e["care_settings"] == ["IPD"]


def test_new_endpoints_normalise_in_the_right_direction():
    angina = resolve_indication("Chronic stable angina")          # lower_better reduction
    assert event_probability_from_primary(angina, 60.0) < event_probability_from_primary(angina, 10.0)
    tocolysis = resolve_indication("Threatened preterm labor")     # higher_better rate
    assert event_probability_from_primary(tocolysis, 80.0) < event_probability_from_primary(tocolysis, 20.0)
    anticoag = resolve_indication("Non-valvular AF; VTE")          # HR, lower_better
    assert event_probability_from_primary(anticoag, 0.65) < event_probability_from_primary(anticoag, 0.95)


def test_pearl_index_is_inverted_lower_is_better():
    """Contraception: a lower Pearl Index must score as higher efficacy."""
    contra = resolve_indication("Contraception")
    assert contra["primary_endpoint"]["key"] == "pearl_index"
    excellent = event_probability_from_primary(contra, 0.2)   # IUD-level
    poor = event_probability_from_primary(contra, 8.0)        # typical-use failure
    assert excellent < poor


def test_every_event_cost_key_exists_in_regional_constants():
    """A registry event must map to a real regional cost, or the engine silently zeroes."""
    from core.constants import REGIONAL_CONSTANTS
    for region, consts in REGIONAL_CONSTANTS.items():
        for key, entry in INDICATION_REGISTRY.items():
            ck = entry["event"]["cost_key"]
            assert ck in consts, f"{region} missing cost key '{ck}' needed by '{key}'"
