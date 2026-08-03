"""
Guards against the platform inventing numbers.

Each test here corresponds to a real defect found in review, where a
plausible-looking figure was manufactured and shown to the user as fact.
"""
import os
import sys
import inspect
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def _source_of(func):
    return inspect.getsource(func)


def test_no_generic_pap_scheme_is_auto_applied():
    """The engine halved every out-of-pocket drug by auto-applying "Buy 1 Get 1 Free".

    A scheme may only be applied when the drug record names a verified one.
    """
    import server
    src = _source_of(server.calculate_period_costs)
    # The old defect: picking a scheme purely by ranking the generic table.
    assert "min(region_paps" not in src, "A generic PAP scheme is being auto-selected again"
    assert "drug_pap_code" in src, "Scheme selection must be gated on the drug's verified code"


def test_regional_price_returns_none_when_unresolved():
    """get_regional_price used to fall back to a flat 15,000/month for anything unknown."""
    import server
    src = _source_of(server.get_regional_price)
    assert '"monthly_price": None' in src, "Unresolved prices must be None, not a default figure"


def test_pap_and_dossier_refuse_without_a_price():
    """Both endpoints previously substituted a 1,000,000 headline price."""
    import server
    for func in (server.recommend_pap, server.generate_dossier):
        src = _source_of(func)
        assert "1000000" not in src, f"{func.__name__} still has a fabricated default price"
        assert "422" in src, f"{func.__name__} must refuse rather than invent a price"


def test_value_engine_returns_none_without_inputs():
    """No primary endpoint => no fabricated event probability or liability."""
    import server
    out = server.calculate_value_engine(None, "Heart Failure", None, "IN")
    assert out["event_probability"] is None
    assert out["c_event"] is None
    assert out["total_liability"] is None
    assert out["data_incomplete"] is True


def test_seeder_does_not_invent_safety_rates():
    """The workbook has no safety data; per-category AE rates were being invented."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "seed_from_workbook.py")).read()
    assert '"drug_severe_ae_rate": None' in src
    assert '"competitor_severe_ae_rate": None' in src
    assert not re.search(r"toxic_rate\s*=\s*0\.\d", src), "Per-category AE rates are being fabricated again"


def test_seeder_does_not_invent_prices():
    """Missing prices were being replaced with a flat 100."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "seed_from_workbook.py")).read()
    assert "else 100.0" not in src, "Missing prices are being backfilled with a default again"


def test_competitor_price_is_not_derived_from_the_drug_price():
    """The seeder set competitor price to 50% of the drug's — an invented fact."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "seed_from_workbook.py")).read()
    assert "price * 0.5" not in src, "Competitor price is being fabricated from the drug price again"


def test_model_assumptions_are_declared_not_hidden():
    """Economic parameters are assumptions; they must be registered and flagged."""
    from core.constants import MODEL_ASSUMPTIONS, unsourced_assumptions
    for key in ("major_event_cost", "monthly_salary", "setting_coverage_share",
                "retail_mrp_multiplier", "endpoint_scaling"):
        assert key in MODEL_ASSUMPTIONS, f"{key} must be declared in the assumptions register"
        assert "sourced" in MODEL_ASSUMPTIONS[key]
    # Until real sources are supplied these must report as unsourced.
    assert unsourced_assumptions(), "Placeholders must not silently report as sourced"


def test_boilerplate_programme_text_does_not_drive_assistance():
    """89% of workbook programme entries are category filler, not real programmes."""
    import server
    src = inspect.getsource(server.resolve_applicability)
    assert "programme_is_generic" in src, "Boilerplate programme text is being trusted again"


def test_no_hardcoded_cost_band_label():
    """"Low-Cost Maintenance" was a fixed label shown on every drug, including
    a 20,000/month specialty injectable."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "frontend", "src", "pages", "ExecutiveDashboard.jsx")).read()
    # The label may exist, but only as one branch of a price-derived decision.
    assert "global_price_inr" in src.split("Low-Cost Maintenance")[0][-1200:], \
        "Cost band label must be derived from the drug's price, not hardcoded"
    assert "High-Cost Specialty" in src, "Price banding is missing"


def test_market_scan_does_not_assert_absence_of_threats():
    """Claiming "no threats detected" without running a scan is an assertion."""
    import server
    src = inspect.getsource(server.web_sweeper_news)
    assert "no immediate patent or generic threats detected in recent intelligence audits" not in src, \
        "The platform is asserting an absence of threats it never checked for"


def test_no_hardcoded_indication_approval_year():
    """A leftover rule set the approval year to 2022 for any indication
    containing "endometrial" — a hardcoded value from the oncology era."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "frontend", "src", "pages", "ExecutiveDashboard.jsx")).read()
    assert "endometrial" not in src.lower(), "Hardcoded indication approval year is back"
    assert "approvalYear = '2022'" not in src


def test_verified_facts_supersede_the_workbook_in_the_ui():
    """Verification must be applied, not merely recorded. The database held
    both "Jan 2024" (workbook) and 2021 (FDA label) and the UI showed the
    workbook value."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "frontend", "src", "pages", "ExecutiveDashboard.jsx")).read()
    assert "verified_facts?.us_initial_approval_year" in src, \
        "The UI is not preferring the verified approval year"
    # And the provenance must be visible to the user.
    assert "Unverified" in src and "Verified" in src
