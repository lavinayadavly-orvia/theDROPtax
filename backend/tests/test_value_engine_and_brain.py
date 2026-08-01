"""
Value Engine + Applicability ("the Brain") tests.

Covers the two behaviours the platform is judged on:
  1. No hallucination — missing inputs stay null and are flagged, never invented.
  2. Relevance — the modules and metrics shown match the drug + indication
     (an acute IV bolus is not given a 12-period cash-flow or a PAP; a cheap
     covered oral drug is not pushed a patient-assistance programme).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "droptax_test")

import pytest
import server


# ── Value engine ──────────────────────────────────────────────────────────

def test_value_engine_computes_for_a_resolved_endpoint():
    r = server.calculate_value_engine(0.80, "Heart Failure", 0.09, "IN")
    assert r["data_incomplete"] is False
    assert r["event_probability"] is not None
    assert r["total_liability"] > 0
    assert r["c_event"] is not None and r["c_prod"] is not None
    assert "hospitalisation" in r["event_label"].lower() or "heart" in r["event_label"].lower()


def test_value_engine_returns_nulls_when_primary_endpoint_missing():
    """Anti-hallucination: no primary endpoint → no invented event cost."""
    r = server.calculate_value_engine(None, "Heart Failure", 0.09, "IN")
    assert r["data_incomplete"] is True
    assert r["event_probability"] is None
    assert r["c_event"] is None
    assert r["productivity_loss_months"] is None
    # The AE component is still real because a real AE rate was supplied
    assert r["c_adverse_events"] is not None


def test_value_engine_returns_null_ae_cost_when_ae_rate_missing():
    r = server.calculate_value_engine(0.80, "Heart Failure", None, "IN")
    assert r["c_adverse_events"] is None
    assert r["breakdown"]["adverse_event_cost"] is None


def test_value_engine_with_no_data_at_all_has_null_total():
    r = server.calculate_value_engine(None, "Heart Failure", None, "IN")
    assert r["total_liability"] is None
    assert r["data_incomplete"] is True


def test_value_engine_uses_therapy_area_appropriate_event_cost():
    """A stroke (major event) should cost more than a metabolic complication."""
    stroke = server.calculate_value_engine(20.0, "Acute Ischemic Stroke", 0.05, "IN")
    diabetes = server.calculate_value_engine(0.5, "Type 2 Diabetes", 0.05, "IN")
    assert stroke["c_event"] > diabetes["c_event"]


def test_value_engine_is_region_aware():
    india = server.calculate_value_engine(0.80, "Heart Failure", 0.09, "IN")
    singapore = server.calculate_value_engine(0.80, "Heart Failure", 0.09, "SG")
    assert india["currency_symbol"] == "₹"
    assert singapore["currency_symbol"] == "S$"
    assert india["total_liability"] != singapore["total_liability"]


def test_value_engine_has_no_oncology_keys():
    r = server.calculate_value_engine(0.80, "Heart Failure", 0.09, "IN")
    blob = repr(r).lower()
    for term in ("pfs", "p_crash", "t_leak", "toxicity_tax", "c_toxicity", "grade_34"):
        assert term not in blob


# ── The Brain: applicability ──────────────────────────────────────────────

def test_acute_iv_bolus_suppresses_cashflow_adherence_and_pap():
    """Tenecteplase: one-time IV bolus in hospital — no cash flow, no PAP."""
    drug = {"route": "iv_bolus", "treatment_model": "acute_single_dose"}
    a = server.resolve_applicability(drug, "Acute Ischemic Stroke", 80000, "IN")

    assert a["treatment_model"] == "acute_single_dose"
    assert a["feasible_settings"] == ["IPD"]
    assert a["duration_periods"] == 1
    assert a["modules"]["period_cash_flow"] is False
    assert a["modules"]["adherence"] is False
    assert a["modules"]["pap_deal_architect"] is False
    assert a["financial_assistance"]["relevant"] is False
    # Clinical + value modules always apply
    assert a["modules"]["tpp_benchmarker"] is True
    assert a["modules"]["value_engine"] is True


def test_ipd_drug_is_covered_and_home_is_not_feasible():
    drug = {"route": "iv_bolus", "treatment_model": "acute_single_dose"}
    a = server.resolve_applicability(drug, "Acute Ischemic Stroke", 80000, "IN")
    assert a["coverage_by_setting"]["IPD"]["coverage"] == "covered"
    assert a["coverage_by_setting"]["IPD"]["price_basis"] == "institutional_tender"
    assert a["coverage_by_setting"]["HOME"]["feasible"] is False


def test_cheap_covered_oral_chronic_drug_needs_no_assistance():
    """Vymada (sacubitril/valsartan) ~Rs4,500/mo — low burden, no PAP."""
    drug = {"route": "oral", "treatment_model": "chronic_ongoing"}
    a = server.resolve_applicability(drug, "Heart Failure", 4500, "IN")

    assert a["treatment_model"] == "chronic_ongoing"
    assert a["feasible_settings"] == ["HOME"]
    assert a["modules"]["period_cash_flow"] is True
    assert a["financial_assistance"]["relevant"] is False
    assert a["financial_assistance"]["tier"] == "none"


def test_expensive_home_drug_triggers_financial_assistance():
    """High-cost self-administered drug with an excluded home setting → PAP."""
    drug = {"route": "sc_injection", "treatment_model": "chronic_ongoing"}
    a = server.resolve_applicability(drug, "Chronic Weight Management", 35000, "IN")

    assert a["coverage_gap"]["exists"] is True
    assert a["financial_assistance"]["relevant"] is True
    assert a["financial_assistance"]["tier"] in {"copay_support", "full_pap"}
    assert a["modules"]["pap_deal_architect"] is True


def test_home_setting_costs_more_than_the_covered_institutional_price():
    """The same drug at home is retail MRP and unreimbursed — the core nuance."""
    drug = {"route": "sc_injection", "treatment_model": "chronic_ongoing"}
    a = server.resolve_applicability(drug, "Osteoporosis", 18000, "IN")

    home = a["coverage_by_setting"]["HOME"]
    opd = a["coverage_by_setting"]["OPD"]
    assert home["price_basis"] == "retail_mrp"
    assert home["coverage"] == "excluded"
    assert home["patient_oop_est"] > opd["patient_oop_est"]


def test_coverage_rules_differ_by_region():
    """India excludes home/retail; Singapore gives partial support."""
    drug = {"route": "oral", "treatment_model": "chronic_ongoing"}
    india = server.resolve_applicability(drug, "Type 2 Diabetes", 8000, "IN")
    singapore = server.resolve_applicability(drug, "Type 2 Diabetes", 220, "SG")

    assert india["coverage_by_setting"]["HOME"]["coverage"] == "excluded"
    assert singapore["coverage_by_setting"]["HOME"]["coverage"] == "conditional"


def test_unknown_route_is_flagged_and_conservative():
    """Anti-hallucination: unknown route must be flagged, never assumed favourable."""
    a = server.resolve_applicability({}, "Some Unlisted Condition XYZ", 50000, "IN")
    assert a["route"] == "unknown"
    assert any(i["field"] == "route" for i in a["issues"])
    # Conservative default: treated as home/retail, which is NOT covered
    assert a["coverage_by_setting"]["HOME"]["coverage"] == "excluded"


def test_registry_supplies_defaults_when_drug_metadata_is_absent():
    """A known indication is structured correctly even with no drug-level data."""
    a = server.resolve_applicability({}, "Acute Ischemic Stroke", 80000, "IN")
    assert a["treatment_model"] == "acute_single_dose"
    assert a["route"] == "iv_bolus"
    assert a["modules"]["pap_deal_architect"] is False


# ── Category routing ──────────────────────────────────────────────────────

def test_get_drug_category_by_indication_routes_correctly():
    assert server.get_drug_category_by_indication("Heart Failure") == "CVD"
    assert server.get_drug_category_by_indication("Acute Ischemic Stroke") == "CVS"
    assert server.get_drug_category_by_indication("Obesity") == "Metabolic"
    assert server.get_drug_category_by_indication("Osteoporosis") == "Women's Health"
    # Unknown falls back to a neutral default — never "Oncology"
    assert server.get_drug_category_by_indication("Unlisted") == "CardioMetabolic"
